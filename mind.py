from datetime import datetime
from flask import Flask,render_template,url_for,request,redirect,flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, current_user, logout_user, login_required
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from waitress import serve
import re
userFormat=".{5,10}"
emailFormat="[f,h]2020.{4}@pilani.bits-pilani.ac.in"
phoneFormat="[0-9]{10}"
passwordFormat=".{5,20}"

from questions import *

app=Flask(__name__,static_url_path='/static')
app.config['SECRET_KEY'] = 'you-cant-guess'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['RATELIMIT_APPLICATION'] = "4/second;12/minute"
db=SQLAlchemy(app)
bcrypt=Bcrypt(app)
login_manager=LoginManager(app)
limiter = Limiter(app,key_func=get_remote_address)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized_callback():
    flash("You have not logged in","fail")
    return redirect(url_for('home'))

class User(db.Model,UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(10), unique=True, nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    phone = db.Column(db.String(10), unique=True, nullable=False)
    password = db.Column(db.String(20), nullable=False)
    stage = db.Column(db.Integer, default=0)
    recentTime = db.Column(db.DateTime, nullable=False, default=datetime.now)

    def __repr__(self):
        return f"User({self.username} , {self.email} , {self.stage+1} , {self.recentTime})"

@app.errorhandler(429)
def toomanyreq(e):
    if current_user.is_authenticated:
        print(current_user.username+" "+current_user.email)
    return "<h3>Too many requests!</h3><h1>Chill...</h1><h4>Try again in sometime</h4>", 429

@app.route('/')
def home():
    if current_user.is_authenticated:
        flash("Already Logged In",'success')
        return redirect(url_for('question'))
    return render_template('home.html',userFormat=userFormat,emailFormat=emailFormat,phoneFormat=phoneFormat,passwordFormat=passwordFormat)


@app.route('/register',methods=['POST','GET'])
def register():
    if current_user.is_authenticated:#check if logged in
        flash("Already Logged In",'success')
        return redirect(url_for('question'))

    if request.method == 'POST':#if form submitted
        if not request.form.get('username') or not request.form.get('email') or not request.form.get('password') or not request.form.get('phone'):#if all details not entered
            flash("You Must Enter All Details","fail")
            return redirect(url_for('home'))

        if not re.match(userFormat,request.form.get('username')):#check format
            flash("Username must be 5 to 10 characters long","fail")
            return redirect(url_for('home'))
        if not re.match(passwordFormat,request.form.get('password')):
            flash("Password must be 5 to 20 characters long","fail")
            return redirect(url_for('home'))
        if not re.match(emailFormat,request.form.get('email')):
            flash("Email must be of BITS Mail format","fail")
            return redirect(url_for('home'))
        if not re.match(phoneFormat,request.form.get('phone')):
            flash("Enter 10 digit Phone Number","fail")
            return redirect(url_for('home'))

        if User.query.filter_by(username=request.form.get('username')).first():#if user exists
            flash("Username exists, use another or Login",'fail')
            return redirect(url_for('home'))
        elif User.query.filter_by(email=request.form.get('email')).first():
            flash("Email exists, use another or Login",'fail')
            return redirect(url_for('home'))
        elif User.query.filter_by(phone=request.form.get('phone')).first():
            flash("Phone number exists, use another or Login",'fail')
            return redirect(url_for('home'))
        else:#create new user
            hashed_password = bcrypt.generate_password_hash(request.form.get('password')).decode('utf-8')
            user = User(username=request.form.get('username'),email=request.form.get('email'),
                        phone=request.form.get('phone'),password=hashed_password)
            db.session.add(user)
            db.session.commit()
            flash("Account Created Successfully!",'success')
            login_user(user)
            return redirect(url_for('question'))
    flash("Enter Details First","fail")
    return redirect(url_for('home'))


@app.route('/login',methods=['POST','GET'])
def login():
    if current_user.is_authenticated:#if logged in
        flash("Already Logged In",'success')
        return redirect(url_for('question'))

    if request.method == 'POST':#if form submitted
        if not request.form.get('username') or not request.form.get('password'):#if all details not entered
            flash("You Must Enter All Details","fail")
            return redirect(url_for('home'))

        if not re.match(userFormat,request.form.get('username')):#check format
            flash("Username must be 5 to 10 characters long","fail")
            return redirect(url_for('home'))
        if not re.match(passwordFormat,request.form.get('password')):
            flash("Password must be 5 to 20 characters long","fail")
            return redirect(url_for('home'))

        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and bcrypt.check_password_hash(user.password, request.form.get('password')):#if user exists
            login_user(user)
            flash("Logged In Successfully",'success')
            return redirect(url_for('question'))
        else:#if user does not exist
            flash("Username/Password does not match, try again or Register",'fail')
            return redirect(url_for('home'))

    flash("Enter Details First","fail")
    return redirect(url_for('home'))


@app.route('/solve',methods=['POST','GET'])
@login_required
def question():
    if current_user.stage >= len(questionSet):
        return redirect(url_for('finished'))
    questions = questionSet[current_user.stage]
    answers = answerSet[current_user.stage]
    links = list(questions.values()).count("none")
    if request.method == 'POST':
        for index in range(len(questions)):
            if list(questions.values())[index] != 'none':
                if not request.form.get(f"question-{index+1}"):
                    flash("You must attempt all questions",'fail')
                    return redirect(url_for('question'))
                elif request.form.get(f"question-{index+1}") != answers[index]:
                    flash("One(or more) of the answers is wrong",'fail')
                    return redirect(url_for('question'))
        current_user.stage = current_user.stage+1
        current_user.recentTime = datetime.now()
        if current_user.stage < len(questionSet)-1:
            flash(f"Stage {current_user.stage} cleared!",'success')
        db.session.commit()
        return redirect(url_for('question'))
    return render_template('questionPage.html',questions=enumerate(questions.items()),
                            stage=current_user.stage,name=current_user.username,leaderboard=getLeaderboard(),
                            links=links,length=len(questions),images=imageSet[current_user.stage])

@app.route('/solve/<link>')
@login_required
def special(link):
    if current_user.stage >= len(questionSet):
        return redirect(url_for('finished'))
    questions = questionSet[current_user.stage]
    answers = answerSet[current_user.stage]
    if link in answers and list(questions.values())[answers.index(link)] == 'none':
        current_user.stage = current_user.stage+1
        current_user.recentTime = datetime.now()
        if current_user.stage < len(questionSet)-1:
            flash(f"Stage {current_user.stage} cleared!",'success')
        db.session.commit()
        return f'''Right answer, <a href=\"{ url_for('question') }\">continue</a><br>
                    <img src="/static/rightmeme{ current_user.stage }.jpg">'''
    else:
        return f'''Wrong answer, <a href=\"{ url_for('question') }\">try again</a><br>
                    <img src="/static/wrongmeme{ current_user.stage+1 }.jpg">'''

@app.route('/congrats')
@login_required
def finished():
    if current_user.stage < len(questionSet):
        flash("You have not completed the test",'fail')
        return redirect(url_for('question'))
    return render_template("congrats.html",leaderboard=getLeaderboard(),name=current_user.username)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged Out Successfully",'success')
    return redirect(url_for('home'))

#@app.route('/reset/<stage>')
#@login_required
#def reset(stage):
#    current_user.stage = int(stage)-1
#    current_user.recentTime = datetime.now()
#    db.session.commit()
#    return redirect(url_for('question'))

def getLeaderboard():
    users = User.query.order_by(User.stage.desc(),User.recentTime).limit(10)
    leaderboard = []
    for i,user in enumerate(users):
        stage = f"Stage {user.stage}"
        if user.stage >= len(questionSet):
            stage = "Finished"
        elif user.stage == 0:
            stage = "Started"
        time = str(int((datetime.now()-user.recentTime).seconds/3600))+" hours ago"
        if time[0]=='0':
            time = str(int((datetime.now()-user.recentTime).seconds/60))+" minutes ago"
        if time[0]=='0':
            time = str(int((datetime.now()-user.recentTime).seconds))+" seconds ago"
        leaderboard.append('<td>{}</td><td>: {} ,</td><td>{}</td>'.format(user.username,stage,time))
    return leaderboard

if __name__ == '__main__':
    #app.run(debug=False,host='0.0.0.0')    #local network with debug
    # app.run(debug=True)                    #locl machine with debug
    #serve(app,host='0.0.0.0',port=5000)     #for hosting
    app.run(host='0.0.0.0')
