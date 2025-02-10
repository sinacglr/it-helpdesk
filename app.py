from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from forms import RegisterForm, LoginForm, TicketForm
from models import db, User, Ticket, Comment

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///helpdesk.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False, default="employee")

class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    agent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    subject = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="open")
    created_at = db.Column(db.DateTime, default=db.func.now())

    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('created_tickets', lazy=True))
    agent = db.relationship('User', foreign_keys=[agent_id], backref=db.backref('assigned_tickets', lazy=True))
    comments = db.relationship('Comment', backref='ticket', lazy=True, cascade="all, delete")

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

    user = db.relationship('User', backref=db.backref('comments', lazy=True))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return redirect(url_for('register'))

@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        role = "employee"
        if form.email.data.endswith("@itcompany.com"):
            role = "it"
        if form.email.data.endswith("@customer.com"):
            role = "customer"
        user = User(name=form.name.data, email=form.email.data, password=hashed_password, role=role)
        db.session.add(user)
        db.session.commit()
        flash("Successfully Signed Up! You can login now.", "success")
        return redirect(url_for("login"))
    return render_template("register.html", form=form)

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for("dashboard"))
        else:
            flash("Incorrect email or password.", "danger")
    return render_template("login.html", form=form)

@app.route("/create_ticket", methods=["GET", "POST"])
@login_required
def create_ticket():
    form = TicketForm()
    if form.validate_on_submit():
        assigned_agent = User.query.filter_by(email=form.to.data).first()

        if not assigned_agent:
            flash("No user found with that email!", "danger")
            return redirect(url_for("create_ticket"))
        
        ticket = Ticket(
            user_id=current_user.id,
            agent_id=assigned_agent.id,
            subject=form.subject.data,
            description=form.description.data
        )
        db.session.add(ticket)
        db.session.commit()

        first_comment = Comment(
            ticket_id=ticket.id,
            user_id=current_user.id,
            text=form.description.data
        )
        db.session.add(first_comment)
        db.session.commit()

        flash("Ticket created successfully and assigned to {assigned_agent.name}", "success")
        return redirect(url_for("dashboard"))
    return render_template("create_ticket.html", form=form)

@app.route('/delete_ticket/<int:ticket_id>', methods=['DELETE'])
def delete_ticket(ticket_id):
    ticket = Ticket.query.get(ticket_id)
    if ticket:
        db.session.delete(ticket)
        db.session.commit()
        return jsonify({"message": "Ticket deleted successfully"}), 200
    return jsonify({"message": "Ticket not found"}), 400

@app.route('/change_ticket_status/<int:ticket_id>', methods=['POST'])
def change_ticket_status(ticket_id):
    ticket = Ticket.query.get(ticket_id)

    if not ticket:
        flash("Ticket not found.", "danger")
        return redirect(url_for('dashboard'))
    
    new_status = request.form.get("status")
    if new_status in ["open", "pending", "closed"]:
        ticket.status = new_status
        db.session.commit()
        flash("Ticket status updated successfully", "success")

    return redirect(url_for('view_ticket', ticket_id=ticket.id))
    

@app.route("/dashboard")
@login_required
def dashboard():
    status_filter = request.args.get("status")

    if current_user.role == "it":
        tickets = Ticket.query.filter_by(agent_id=current_user.id)
    else:
        tickets = Ticket.query.filter_by(user_id=current_user.id)

    if status_filter:
        tickets = tickets.filter_by(status=status_filter)

    tickets = tickets.all()

    return render_template("dashboard.html", tickets=tickets)

@app.route("/ticket/<int:ticket_id>")
@login_required
def view_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    return render_template("view_ticket.html", ticket=ticket)

@app.route("/all_tickets")
@login_required
def all_tickets():
    if current_user.role != "it":
        flash("You dont have permission to view this page!", "danger")
        return redirect(url_for("dashboard"))
    
    tickets = Ticket.query.all()
    return render_template("all_tickets.html", tickets=tickets)

@app.route("/update_ticket_status/<int:ticket_id>", methods=["POST"])
@login_required
def update_ticket_status(ticket_id):
    if current_user.role != "it":
        flash("You don't have permission to update tickets!", "danger")
        return redirect(url_for("dashboard"))
    
    ticket = Ticket.query.get_or_404(ticket_id)
    ticket.status = request.form["status"]

    if "agent" in request.form and request.form["agent"]:
        agent = User.query.filter_by(id=request.form["agent"]).first()
        if agent:
            ticket.agent_id = agent.id

    db.session.commit()
    flash("Ticket status updated!", "success")
    return redirect(url_for("all_tickets"))

@app.route("/add_comment/<int:ticket_id>", methods=["POST"])
@login_required
def add_comment(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    new_comment = Comment(ticket_id=ticket.id, user_id=current_user.id, text=request.form["comment_text"])
    db.session.add(new_comment)
    db.session.commit()
    flash("Comment added!", "success")
    return redirect(url_for("view_ticket", ticket_id=ticket.id))
    

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

if __name__=="__main__":
    with app.app_context():
        db.create_all()
        print("Database successfully recreated!")
    app.run(debug=True)
