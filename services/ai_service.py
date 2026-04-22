"""
Google Gemini AI integration for the barbershop assistant.
Responds in Uzbek language, staying in-context for the barbershop.
"""
import google.generativeai as genai
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """
Sen "Barbershop Elite" sartaroshxonasi uchun maxsus AI yordamchisan.
Sening vazifang:
1. Foydalanuvchilarga xizmatlar haqida ma'lumot berish.
2. Soch turmagi va soqol bo'yicha maslahat berish.
3. Narxlar va ish vaqti haqida ma'lumot berish.

Muhim qoidalar:
- FAQAT O'zbek tilida javob ber.
- Javoblar qisqa, do'stona va tabiiy bo'lsin (3-5 gap).
- Faqat sartaroshxona mavzusida javob ber. Boshqa mavzularga "Bu savolga javob berolmayman, lekin soch/soqol haqida yordam bera olaman!" de.
- Harakat qilma da'vo qilma, real amaliy maslahat ber.

Xizmatlar va narxlar:
- ✂️ Soch qisqartirish: $10
- 🪒 Soqol tekislash: $7
- 💈 Kombo (soch + soqol): $15
- ⭐ Premium stil: $20

Ish vaqti: 09:00 - 21:00, har kuni
Manzil: Toshkent, Chilonzor

Soch turmagi bo'yicha maslahatlar:
- Dumaloq yuz: Pompadour, Quiff, Fade – yuzni uzunroq ko'rsatadi
- Oval yuz: Istalgan turmak yarashadi
- Tuxumsimon yuz: Undercut, Textured Crop – klassik ko'rinish
- To'g'ri burchakli yuz: Layered cut, Side part – burchakni yumshatadi
- Uchburchak yuz: Volume tepada, qisqa yon – muvozanat beradi
"""

# We keep conversation history per user in memory (can be moved to Redis for production)
_user_histories: dict[int, list] = {}


def _get_model():
    return genai.GenerativeModel(model_name="gemini-pro")


async def ask_ai(user_id: int, user_message: str) -> str:
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_google_gemini_api_key_here":
        return "🤖 AI yordamchi hozir o'chirilgan."

    try:
        model = _get_model()
        history = _user_histories.get(user_id, [])
        chat = model.start_chat(history=history)
        
        # Prepend system prompt if history is empty
        full_message = user_message
        if not history:
            full_message = f"{SYSTEM_PROMPT}\n\nFoydalanuvchi: {user_message}"
            
        response = await chat.send_message_async(full_message)
        _user_histories[user_id] = chat.history[-20:]
        return response.text
    except Exception as e:
        import logging
        logging.error(f"Gemini AI Error: {e}")
        return (
            f"⚠️ AI bilan muloqotda xatolik yuz berdi.\n"
            f"Iltimos, qaytadan urinib ko'ring yoki /cancel buyrug'ini bering."
        )


def reset_ai_history(user_id: int) -> None:
    """Clears the user's AI conversation history."""
    _user_histories.pop(user_id, None)
