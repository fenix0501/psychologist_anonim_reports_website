from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from functools import wraps
import pickle
import re
import string
import hashlib
from models import Base, Ticket, Token, Message, Tag, AuditLog, UserAdmin
import os

SQLALCHEMY_DATABASE_URL = "sqlite:///./anti_bullying.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def initialize_default_admin():
    db = SessionLocal()
    try:
        admin_exists = db.query(UserAdmin).first()
        if not admin_exists:
            default_password = "psychologist123"
            password_hash = hashlib.sha256(default_password.encode()).hexdigest()
            
            default_admin = UserAdmin(
                username="psychologist",
                role="psychologist",
                permissions="view_tickets,view_messages,respond_to_tickets,manage_tags",
                password_hash=password_hash,
                is_active=True
            )
            db.add(default_admin)
            db.commit()
            print("Default admin user created: psychologist / psychologist123")
        else:
            print("Admin user already exists, skipping default creation.")
    except Exception as e:
        print(f"Error initializing default admin: {e}")
    finally:
        db.close()

initialize_default_admin()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"detail": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function

print("Loading neural network...")
with open('lgbm_model_toxic_.pkl', 'rb') as f:
    model = pickle.load(f)
with open('tfidf_vectorizer.pkl', 'rb') as f:
    vectorizer = pickle.load(f)
print("Model is ready!")

def preprocess_text(text: str):
    text = text.lower()
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'#\w+', '', text)
    text = re.sub(f'[{re.escape(string.punctuation)}]', '', text)
    text = re.sub(r'\d+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

app = Flask(__name__)
app.secret_key = os.urandom(24)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def log_action(db, action: str, performed_by: str, target_entity: str, target_id: int):
    audit_log = AuditLog(
        action=action,
        performed_by=performed_by,
        target_entity=target_entity,
        target_id=target_id
    )
    db.add(audit_log)
    db.commit()

def classify_text_with_ml(text: str):
    clean_text = preprocess_text(text)
    vectorized_text = vectorizer.transform([clean_text])
    prediction = model.predict(vectorized_text)[0]
    probabilities = model.predict_proba(vectorized_text)[0]
    confidence = max(probabilities)

    result = {
        "category": prediction,
        "confidence": float(confidence),
        "is_dangerous": prediction in ['suicide', 'offline_crime', 'weapons', 'threat'],
        "priority": "high" if prediction in ['suicide', 'offline_crime', 'weapons', 'threat'] else "medium"
    }

    return result

@app.route('/api/report', methods=['POST'])
def create_report():
    data = request.get_json(silent=True) or {}
    
    text = (data.get('text') or '').strip()
    if not text:
        return jsonify({"detail": "Report text is required"}), 400

    ml_result = classify_text_with_ml(text)

    db = next(get_db())
    
    ticket = Ticket(
        text=text,
        category=ml_result["category"],
        priority=ml_result["priority"],
        status="new"
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    ticket_id = ticket.id

    token_value = Token.generate_token()
    token = Token(
        token_value=token_value,
        ticket_id=ticket_id
    )
    db.add(token)
    db.commit()

    message = Message(
        ticket_id=ticket_id,
        role="student",
        text=text
    )
    db.add(message)
    db.commit()

    tag = Tag(
        ticket_id=ticket_id,
        tag_name=ml_result["category"],
        probability=ml_result["confidence"]
    )
    db.add(tag)
    db.commit()

    log_action(db, "create_ticket", "anonymous_student", "ticket", ticket_id)

    response_data = {
        "ticket_id": ticket_id,
        "token": token_value,
        "message": "Report created successfully. Please save this token to continue the conversation.",
        "ml_analysis": ml_result
    }

    db.close()

    return jsonify(response_data)

@app.route('/api/chat', methods=['POST'])
def send_message():
    data = request.get_json(silent=True) or {}
    token_value = data.get('token')
    message_text = (data.get('message') or '').strip()

    if not token_value:
        return jsonify({"detail": "Token is required"}), 400
    if not message_text:
        return jsonify({"detail": "Message is required"}), 400

    db = next(get_db())
    
    token_record = db.query(Token).filter(Token.token_value == token_value).first()
    if not token_record:
        db.close()
        return jsonify({"detail": "Invalid token"}), 404

    message = Message(
        ticket_id=token_record.ticket_id,
        role="student",
        text=message_text
    )
    db.add(message)
    db.commit()

    token_record.last_access = datetime.utcnow()
    db.commit()

    log_action(db, "send_message", "student", "message", message.id)

    response_data = {"message": "Message sent successfully"}

    db.close()

    return jsonify(response_data)

@app.route('/api/chat/token', methods=['POST'])
def get_chat_history_by_token():
    data = request.get_json(silent=True) or {}
    token_value = data.get('token')

    if not token_value:
        return jsonify({"detail": "Token is required"}), 400

    db = next(get_db())
    
    token_record = db.query(Token).filter(Token.token_value == token_value).first()
    if not token_record:
        db.close()
        return jsonify({"detail": "Invalid token"}), 404

    messages = db.query(Message).filter(Message.ticket_id == token_record.ticket_id).order_by(Message.timestamp).all()

    token_record.last_access = datetime.utcnow()
    db.commit()

    ticket_id = token_record.ticket_id
    messages_data = [
        {
            "role": msg.role,
            "text": msg.text,
            "timestamp": msg.timestamp.isoformat()
        } for msg in messages
    ]

    db.close()

    return jsonify({
        "ticket_id": ticket_id,
        "messages": messages_data
    })

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not username or not password:
        return jsonify({"detail": "Username and password are required"}), 400

    db = next(get_db())

    password_hash = hashlib.sha256(password.encode()).hexdigest()

    user = db.query(UserAdmin).filter(
        UserAdmin.username == username,
        UserAdmin.password_hash == password_hash,
        UserAdmin.is_active.is_(True)
    ).first()

    if not user:
        db.close()
        return jsonify({"detail": "Invalid credentials"}), 401

    session['user_id'] = user.id
    session['username'] = user.username
    session['role'] = user.role

    user_data = {
        "success": True,
        "user_id": user.id,
        "username": user.username,
        "role": user.role
    }

    db.close()

    return jsonify(user_data)

@app.route('/api/admin/tickets', methods=['GET'])
@login_required
def get_tickets():
    status = request.args.get('status')
    priority = request.args.get('priority')
    category = request.args.get('category')
    sort_by = request.args.get('sort_by', 'created_at')
    order = request.args.get('order', 'desc')
    skip = int(request.args.get('skip', 0))
    limit = int(request.args.get('limit', 20))

    db = next(get_db())
    
    query = db.query(Ticket)

    if status:
        query = query.filter(Ticket.status == status)
    if priority:
        query = query.filter(Ticket.priority == priority)
    if category:
        query = query.filter(Ticket.category == category)

    if sort_by == "created_at":
        if order == "asc":
            query = query.order_by(asc(Ticket.created_at))
        else:
            query = query.order_by(desc(Ticket.created_at))
    elif sort_by == "priority":
        if order == "asc":
            query = query.order_by(asc(Ticket.priority))
        else:
            query = query.order_by(desc(Ticket.priority))
    elif sort_by == "status":
        if order == "asc":
            query = query.order_by(asc(Ticket.status))
        else:
            query = query.order_by(desc(Ticket.status))

    tickets = query.offset(skip).limit(limit).all()

    result = []
    for ticket in tickets:
        tags = db.query(Tag).filter(Tag.ticket_id == ticket.id).all()

        last_message = db.query(Message).filter(
            Message.ticket_id == ticket.id
        ).order_by(desc(Message.timestamp)).first()

        ticket_data = {
            "id": ticket.id,
            "text_preview": ticket.text[:100] + "..." if len(ticket.text) > 100 else ticket.text,
            "category": ticket.category,
            "priority": ticket.priority,
            "status": ticket.status,
            "created_at": ticket.created_at.isoformat(),
            "updated_at": ticket.updated_at.isoformat(),
            "tags": [{"tag_name": tag.tag_name, "probability": tag.probability} for tag in tags],
            "last_message": {
                "role": last_message.role,
                "text": last_message.text,
                "timestamp": last_message.timestamp.isoformat()
            } if last_message else None
        }
        result.append(ticket_data)

    db.close()

    return jsonify({"tickets": result})

@app.route('/api/admin/tickets/<int:ticket_id>/status', methods=['PUT'])
@login_required
def change_ticket_status(ticket_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get('status')

    if new_status not in {"new", "in_progress", "resolved"}:
        return jsonify({"detail": "Invalid status"}), 400

    db = next(get_db())
    
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        db.close()
        return jsonify({"detail": "Ticket not found"}), 404

    old_status = ticket.status
    ticket.status = new_status
    ticket.updated_at = datetime.utcnow()
    db.commit()

    log_action(db, f"change_status_from_{old_status}_to_{new_status}", "admin", "ticket", ticket_id)

    response_data = {"message": f"Status updated to {new_status}"}

    db.close()

    return jsonify(response_data)

@app.route('/api/admin/tickets/<int:ticket_id>/priority', methods=['PUT'])
@login_required
def change_ticket_priority(ticket_id):
    data = request.get_json(silent=True) or {}
    new_priority = data.get('priority')

    if new_priority not in {"low", "medium", "high"}:
        return jsonify({"detail": "Invalid priority"}), 400

    db = next(get_db())
    
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        db.close()
        return jsonify({"detail": "Ticket not found"}), 404

    old_priority = ticket.priority
    ticket.priority = new_priority
    ticket.updated_at = datetime.utcnow()
    db.commit()

    log_action(db, f"change_priority_from_{old_priority}_to_{new_priority}", "admin", "ticket", ticket_id)

    response_data = {"message": f"Priority updated to {new_priority}"}

    db.close()

    return jsonify(response_data)

@app.route('/api/admin/tickets/<int:ticket_id>/chat', methods=['GET'])
@login_required
def get_ticket_chat(ticket_id):
    db = next(get_db())
    
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        db.close()
        return jsonify({"detail": "Ticket not found"}), 404

    messages = db.query(Message).filter(Message.ticket_id == ticket_id).order_by(Message.timestamp).all()

    messages_data = [
        {
            "id": msg.id,
            "role": msg.role,
            "text": msg.text,
            "timestamp": msg.timestamp.isoformat()
        } for msg in messages
    ]

    db.close()

    return jsonify({
        "ticket_id": ticket_id,
        "messages": messages_data
    })

@app.route('/api/admin/tickets/<int:ticket_id>/chat', methods=['POST'])
@login_required
def send_admin_message(ticket_id):
    data = request.get_json(silent=True) or {}
    message_text = (data.get('message') or '').strip()

    if not message_text:
        return jsonify({"detail": "Message is required"}), 400

    db = next(get_db())

    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        db.close()
        return jsonify({"detail": "Ticket not found"}), 404

    message = Message(
        ticket_id=ticket_id,
        role="psychologist",
        text=message_text
    )
    db.add(message)
    db.commit()

    if ticket.status != "resolved":
        ticket.status = "in_progress"
        ticket.updated_at = datetime.utcnow()
        db.commit()

    log_action(db, "send_admin_message", "admin", "message", message.id)

    response_data = {"message": "Message sent successfully"}

    db.close()

    return jsonify(response_data)

@app.route('/api/admin/logout', methods=['POST'])
@login_required
def admin_logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"})

@app.route('/api/admin/messages', methods=['GET'])
@login_required
def get_all_messages():
    role_filter = request.args.get('role')
    status_filter = request.args.get('status')
    category_filter = request.args.get('category')

    db = next(get_db())

    query = db.query(Message).join(Ticket)

    if role_filter:
        query = query.filter(Message.role == role_filter)
    if status_filter:
        query = query.filter(Ticket.status == status_filter)
    if category_filter:
        query = query.filter(Ticket.category == category_filter)

    messages = query.order_by(Message.timestamp.desc()).all()

    result = []
    for message in messages:
        ticket = db.query(Ticket).filter(Ticket.id == message.ticket_id).first()
        tags = db.query(Tag).filter(Tag.ticket_id == message.ticket_id).all()
        
        message_data = {
            "id": message.id,
            "ticket_id": message.ticket_id,
            "role": message.role,
            "text": message.text,
            "timestamp": message.timestamp.isoformat(),
            "ticket_category": ticket.category if ticket else None,
            "ticket_priority": ticket.priority if ticket else None,
            "ticket_status": ticket.status if ticket else None,
            "tags": [{"tag_name": tag.tag_name, "probability": tag.probability} for tag in tags]
        }
        result.append(message_data)

    db.close()

    return jsonify({"messages": result})

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/login')
def login_page():
    return render_template("login.html")

@app.route('/admin')
def admin_panel():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login_page'))
    return render_template("admin.html")

@app.route('/chat/<token>')
def chat_page(token):
    return render_template("chat.html", token=token)

@app.route('/about')
def about():
    return render_template("about.html")

@app.route('/how-it-works')
def how_it_works():
    return render_template("how_it_works.html")

@app.route('/contact')
def contact():
    return render_template("contact.html")

@app.route('/resources')
def resources():
    return render_template("resources.html")

@app.route('/faq')
def faq():
    return render_template("faq.html")

@app.route('/privacy-policy')
def privacy_policy():
    return render_template("privacy_policy.html")

@app.route('/terms-of-service')
def terms_of_service():
    return render_template("terms_of_service.html")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
