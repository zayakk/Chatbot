import os
import re
from rest_framework.decorators import api_view
from rest_framework.response import Response
from openai import OpenAI
from .models import Property

# Initialize OpenAI client (make sure OPENAI_API_KEY is set in your environment)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def parse_user_intent(text: str):
    """
    Parse user message and extract intent dict:
    {
        name_only: bool,
        detail_for: Optional[str],
        location: Optional[str],
        area_op: '<='|'>='|None,
        area_value: int|None,
        price_max: int|None
    }
    """
    t = text.lower()
    intent = {
        "name_only": False,
        "detail_for": None,
        "location": None,
        "area_op": None,
        "area_value": None,
        "price_max": None
    }

    # Check if user requests only names
    if "зөвхөн нэр" in t or "нэрийг нь харуул" in t or "анхааралтай нэр" in t:
        intent["name_only"] = True

    # Detail request example: "Гэрийн тухай дэлгэрэнгүй"
    m = re.search(r'(.+?)ийн тухай|(.+?)-ийн тухай', text, re.IGNORECASE)
    if m:
        name = (m.group(1) or m.group(2) or "").strip()
        if name:
            intent["detail_for"] = name

    # Location matching (example cities/districts)
    loc_match = re.search(r'(улаанбаатар|дархан|орхон|сүхбаатар)', t, re.IGNORECASE)
    if loc_match:
        intent["location"] = loc_match.group(0)

    # Area filter: "100-аас доош м2", "100 м2-ээс их", "100 м2"
    m_down = re.search(r'(\d+)[\s-]*(м|м2|м²|метр).*(?:доош|бага)', t, re.IGNORECASE)
    if m_down:
        intent["area_op"] = "<="
        intent["area_value"] = int(m_down.group(1))
    
    m_up = re.search(r'(\d+)[\s-]*(м|м2|м²|метр).*(?:их|ихээс)', t, re.IGNORECASE)
    if m_up:
        intent["area_op"] = ">="
        intent["area_value"] = int(m_up.group(1))
    
    if not intent["area_value"]:
        m_exact = re.search(r'(\d+)[\s-]*(м|м2|м²|метр)', t, re.IGNORECASE)
        if m_exact:
            intent["area_op"] = None
            intent["area_value"] = int(m_exact.group(1))

    # Price filter: "200 сая доош", "200000000 доош"
    m_price = re.search(r'(\d+)[\s]*(?:сая|сая-|).*(?:доош|бага|төгрөг)', t, re.IGNORECASE)
    if m_price:
        price_str = m_price.group(1)
        if "сая" or "say" in t:
            intent["price_max"] = int(price_str) * 1000000
        else:
            intent["price_max"] = int(price_str)

    return intent


@api_view(["POST"])
def chat_with_ai(request):
    """
    Endpoint for real estate chatbot
    """
    user_message = request.data.get("message", "").strip()
    if not user_message:
        return Response({"error": "No message provided"}, status=400)

    try:
        intent = parse_user_intent(user_message)

        properties = Property.objects.all()
        has_filters = False

        if intent["location"]:
            properties = properties.filter(location__icontains=intent["location"])
            has_filters = True

        if intent["area_value"] is not None:
            if intent["area_op"] == "<=":
                properties = properties.filter(area__lte=intent["area_value"])
            elif intent["area_op"] == ">=":
                properties = properties.filter(area__gte=intent["area_value"])
            else:
                properties = properties.filter(area=intent["area_value"])
            has_filters = True

        if intent["price_max"] is not None:
            properties = properties.filter(price__lte=intent["price_max"])
            has_filters = True

        if intent["detail_for"]:
            properties = properties.filter(name__icontains=intent["detail_for"])
            has_filters = True

        if has_filters and not properties.exists():
            return Response({"reply": "Одоогоор таны хүссэн шалгуурт нийцсэн байр олдсонгүй.", "properties": []})

        if not properties.exists():
            return Response({"reply": "Одоогоор байр байхгүй байна.", "properties": []})

        property_list = ""
        properties_data = []
        for p in properties:
            prop_dict = {
                "name": p.name,
                "location": p.location,
                "price": p.price,
                "area": getattr(p, "area", None),
                "description": p.description
            }
            properties_data.append(prop_dict)
            area_str = f", {p.area}м2" if hasattr(p, "area") and p.area else ""
            property_list += f"- {p.name}, {p.location}{area_str}, {p.price}₮, {p.description}\n"

        if intent["name_only"]:
            names_only = "\n".join([p["name"] for p in properties_data])
            system_msg = ("Та real estate assistant. Хэрэглэгч зөвхөн байрнуудын нэрийг асуусан байна. "
                          "Доорх нэрсийн жагсаалтыг харуулж, товч хариулт өгнө үү.")
            user_prompt = f"User асуулт: {user_message}\n\nБайрнуудын нэрс:\n{names_only}"
        elif intent["detail_for"]:
            system_msg = ("Та real estate assistant. Хэрэглэгч тодорхой байрны талаар дэлгэрэнгүй хүссэн байна. "
                          "Доорх өгөгдлийг ашиглан бүрэлдэхүүнтэй хариулт өгнө үү. Нэмэлт мэдээллийг бүү оруул.")
            user_prompt = f"User асуулт: {user_message}\n\nБайрны мэдээлэл:\n{property_list}"
        else:
            system_msg = ("Та real estate assistant. "
                          "Хэрэглэгчийн асуултанд зөвхөн доорх өгөгдлийг ашиглан товч, ойлгомжтой хариулт өгнө. "
                          "Өгөгдөлд байхгүй мэдээллийг бүү нэм.")
            user_prompt = f"User асуулт: {user_message}\n\nБайрнуудын мэдээлэл:\n{property_list}"

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.5
        )
        ai_reply = completion.choices[0].message.content

        return Response({
            "reply": ai_reply,
            "properties": properties_data,
            "count": len(properties_data)
        })

    except Exception as e:
        import traceback
        print(f"Error: {traceback.format_exc()}")
        return Response({"error": f"Server error: {str(e)}"}, status=500)
