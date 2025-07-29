import os
import requests
from flask import Blueprint, request, jsonify
from models import db, Prompt
from dotenv import load_dotenv

load_dotenv()

routes = Blueprint("routes", __name__)

@routes.route("/")
def index():
    return "AI Prompt Tool Running"

@routes.route("/prompts", methods=["POST"])
def create_prompt():
    data = request.get_json()
    question = data.get("question")

    if not question:
        return jsonify({"error": "Question is required"}), 400

    prompt = Prompt(question=question)
    db.session.add(prompt)
    db.session.commit()

    try:
        HF_API_KEY = os.getenv("HF_API_KEY")
        
        models_to_try = [
            "gpt2",
            "microsoft/DialoGPT-medium",
            "facebook/blenderbot-400M-distill",
            "google/flan-t5-small"
        ]
        
        answer = None
        last_error = None
        
        for model_id in models_to_try:
            try:
                hf_url = f"https://api-inference.huggingface.co/models/{model_id}"
                headers = {
                    "Authorization": f"Bearer {HF_API_KEY}",
                    "Content-Type": "application/json"
                }
                
                payload = {"inputs": question}

                response = requests.post(hf_url, headers=headers, json=payload, timeout=30)

                if response.status_code == 503:
                    continue
                
                if response.status_code == 404:
                    continue

                response.raise_for_status()

                if response.text.strip() == "":
                    continue

                try:
                    result = response.json()
                except Exception as json_error:
                    continue

                if isinstance(result, list) and len(result) > 0:
                    if isinstance(result[0], dict):
                        if "generated_text" in result[0]:
                            answer = result[0]["generated_text"]
                        elif "text" in result[0]:
                            answer = result[0]["text"]
                    elif isinstance(result[0], str):
                        answer = result[0]
                elif isinstance(result, dict):
                    if "generated_text" in result:
                        answer = result["generated_text"]
                    elif "text" in result:
                        answer = result["text"]

                if answer and question in answer:
                    answer = answer.replace(question, "").strip()

                if answer and answer.strip():
                    break
                    
            except Exception as e:
                last_error = str(e)
                continue

        if not answer or not answer.strip():
            answer = f"I understand you're asking: '{question}'. I'm currently having trouble accessing AI models, but I've saved your question for when the service is restored."

        prompt.answer = answer
        db.session.commit()

        return jsonify({
            "id": prompt.id,
            "question": prompt.question,
            "answer": answer
        }), 201

    except Exception as e:
        prompt.answer = f"I received your question but encountered a technical issue. Please try again later."
        db.session.commit()
        
        return jsonify({
            "error": "Service temporarily unavailable",
            "details": str(e),
            "id": prompt.id,
            "question": prompt.question,
            "answer": prompt.answer
        }), 503


@routes.route("/prompts/openai", methods=["POST"])
def create_prompt_openai():
    data = request.get_json()
    question = data.get("question")

    if not question:
        return jsonify({"error": "Question is required"}), 400

    try:
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        
        if not OPENAI_API_KEY or OPENAI_API_KEY == "your-openai-key":
            return jsonify({"error": "OpenAI API key not configured"}), 400

        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "user", "content": question}
            ],
            "max_tokens": 150,
            "temperature": 0.7
        }

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )

        response.raise_for_status()
        result = response.json()
        
        answer = result["choices"][0]["message"]["content"]

        prompt = Prompt(question=question, answer=answer)
        db.session.add(prompt)
        db.session.commit()

        return jsonify({
            "id": prompt.id,
            "question": prompt.question,
            "answer": answer
        }), 201

    except Exception as e:
        return jsonify({
            "error": "OpenAI API error",
            "details": str(e)
        }), 500


@routes.route("/prompts/simple", methods=["POST"])
def create_prompt_simple():
    data = request.get_json()
    question = data.get("question")

    if not question:
        return jsonify({"error": "Question is required"}), 400

    question_lower = question.lower().strip()
    
    simple_responses = {
        "hello": "Hello! How can I help you today?",
        "hi": "Hi there! What would you like to know?",
        "what is your name": "I'm an AI assistant powered by Hugging Face models.",
        "how are you": "I'm doing well, thank you for asking!",
        "what is the capital of france": "The capital of France is Paris.",
        "what is ai": "Artificial Intelligence (AI) is the simulation of human intelligence in machines that are programmed to think and learn.",
        "who are you": "I'm an AI assistant designed to help answer your questions and have conversations.",
        "thank you": "You're welcome! Is there anything else I can help you with?",
        "bye": "Goodbye! Feel free to ask me anything anytime.",
        "what is python": "Python is a high-level, interpreted programming language known for its simplicity and versatility.",
        "what is machine learning": "Machine Learning is a subset of AI that enables computers to learn and make decisions from data without being explicitly programmed."
    }
    
    if question_lower in simple_responses:
        answer = simple_responses[question_lower]
    elif any(key in question_lower for key in ["capital", "france"]):
        answer = "The capital of France is Paris."
    elif any(key in question_lower for key in ["python", "programming"]):
        answer = "Python is a popular programming language used for web development, data science, AI, and more."
    elif any(key in question_lower for key in ["ai", "artificial intelligence"]):
        answer = "AI stands for Artificial Intelligence - technology that enables machines to simulate human intelligence."
    elif question_lower.startswith("what is"):
        topic = question_lower.replace("what is", "").strip()
        answer = f"I'd be happy to explain {topic}, but I'm currently running in simple mode. For detailed explanations, please try again when the AI models are available."
    elif "?" in question:
        answer = f"That's an interesting question about '{question}'. I'm currently in simple response mode, but I've saved your question for a more detailed answer when AI models are available."
    else:
        answer = f"Thank you for your message: '{question}'. I'm currently providing simple responses while working to restore full AI capabilities."

    prompt = Prompt(question=question, answer=answer)
    db.session.add(prompt)
    db.session.commit()

    return jsonify({
        "id": prompt.id,
        "question": prompt.question,
        "answer": answer
    }), 201

@routes.route("/prompts", methods=["GET"])
def get_prompts():
    prompts = Prompt.query.all()
    return jsonify([{
        "id": p.id,
        "question": p.question,
        "answer": p.answer,
        "created_at": p.created_at.isoformat() if hasattr(p, 'created_at') else None
    } for p in prompts])

@routes.route("/prompts/<int:prompt_id>", methods=["GET"])
def get_prompt(prompt_id):
    prompt = Prompt.query.get_or_404(prompt_id)
    return jsonify({
        "id": prompt.id,
        "question": prompt.question,
        "answer": prompt.answer,
        "created_at": prompt.created_at.isoformat() if hasattr(prompt, 'created_at') else None
    })

@routes.route("/test-api", methods=["GET"])
def test_api():
    try:
        HF_API_KEY = os.getenv("HF_API_KEY")
        
        test_results = []
        models_to_test = ["gpt2", "microsoft/DialoGPT-medium", "facebook/blenderbot-400M-distill"]
        
        for model_id in models_to_test:
            try:
                hf_url = f"https://api-inference.huggingface.co/models/{model_id}"
                headers = {
                    "Authorization": f"Bearer {HF_API_KEY}",
                    "Content-Type": "application/json"
                }
                
                payload = {"inputs": "Hello, world!"}
                
                response = requests.post(hf_url, headers=headers, json=payload, timeout=10)
                
                test_results.append({
                    "model": model_id,
                    "status": response.status_code,
                    "available": response.status_code in [200, 503],  # 503 means loading
                    "response_preview": response.text[:100] if response.text else "No response"
                })
                
            except Exception as e:
                test_results.append({
                    "model": model_id,
                    "status": "error",
                    "available": False,
                    "error": str(e)
                })
        
        return jsonify({
            "api_key_configured": bool(HF_API_KEY and HF_API_KEY != "your-hf-key"),
            "test_results": test_results,
            "recommendation": "Use /prompts/simple endpoint for reliable responses"
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "api_accessible": False
        })