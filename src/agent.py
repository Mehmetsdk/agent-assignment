import os
import json
from dotenv import load_dotenv
from groq import Groq
from src.tools import TOOL_DEFINITIONS, AVAILABLE_TOOLS

# .env dosyasındaki API anahtarını yükler
load_dotenv()

class TaskAgent:
    def __init__(self):
        # API anahtarının olup olmadığını kontrol et
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key or api_key == "senin_groq_api_anahtarin_buraya_gelecek":
            raise ValueError("Lütfen .env dosyasına geçerli bir GROQ_API_KEY girin!")
            
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"  # Groq'un güncel modeli
        
        # Ajanın kişiliğini ve kurallarını belirleyen Sistem İstemi (System Prompt)
        self.system_prompt = {
            "role": "system",
            "content": (
                "YOU MUST RESPOND ONLY IN ENGLISH. NO OTHER LANGUAGE. "
                "You are a helpful, reliable, and agentic executive assistant. "
                "Your primary goal is to execute user requests by breaking them down into logical steps. "
                "CRITICAL RULES: "
                "1. ALWAYS respond in English, even if the user asks in Turkish or any other language. Translate and respond in English only. "
                "2. If a request lacks essential information (e.g., location, date, time preference, budget), YOU MUST ASK a clear clarifying question before taking action. "
                "3. Use the provided tools to check calendars, search for options, book items, and set reminders. "
                "4. If a tool fails or finds no results, apologize and ask the user how they would like to proceed. "
                "5. Once the task is fully complete, provide a structured final summary stating: What was done, what was booked/found, and any remaining blockers."
            )
        }
        # Modelin konuşmayı hatırlaması için geçmiş tutulur
        self.conversation_history = [self.system_prompt]

    def process_input(self, user_input: str) -> str:
        # Kullanıcının mesajını geçmişe ekle
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # Ajanın birden fazla aracı peş peşe kullanabilmesi için döngü
        while True:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            
            # Eğer model bir araç (tool) kullanmaya karar verdiyse:
            if hasattr(message, 'tool_calls') and message.tool_calls:
                # Modelin araç çağırma isteğini geçmişe kaydet
                self.conversation_history.append(message)
                
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    function_args_str = tool_call.function.arguments
                    
                    try:
                        function_args = json.loads(function_args_str)
                    except json.JSONDecodeError:
                        function_args = {}
                    
                    # src/tools.py içindeki gerçek fonksiyonu bul ve çalıştır
                    if function_name in AVAILABLE_TOOLS:
                        tool_to_call = AVAILABLE_TOOLS[function_name]
                        tool_result = tool_to_call(**function_args)
                    else:
                        tool_result = json.dumps({"error": f"Unknown tool: {function_name}"})
                        
                    # Aracın ürettiği sonucu modele geri gönder
                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": tool_result
                    })
                # Döngü başa döner, model araç sonuçlarını okuyup yeni bir karar verir
            else:
                # Model araç kullanmadıysa, kullanıcıya cevap veriyor
                base_response = message.content
                self.conversation_history.append({"role": "assistant", "content": base_response})
                
                # Final summary isteme mesajı ekle
                self.conversation_history.append({
                    "role": "user",
                    "content": "Please provide a structured final summary with: 1) What was done, 2) What was booked/found, 3) Any remaining blockers. Format it clearly."
                })
                
                # Final summary'yi al
                summary_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.conversation_history,
                )
                
                summary_content = summary_response.choices[0].message.content
                self.conversation_history.append({"role": "assistant", "content": summary_content})
                
                # Kombinasyonu döndür
                return f"{base_response}\n\n{'='*60}\n📋 FINAL SUMMARY:\n{'='*60}\n{summary_content}"
