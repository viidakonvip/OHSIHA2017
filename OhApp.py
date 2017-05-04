from flask import Flask, render_template, json, request, session, url_for, jsonify, redirect, flash
from flaskext.mysql import MySQL
from werkzeug import generate_password_hash, check_password_hash
#from forms import ContactForm
from flask_mail import Message, Mail
from flask_wtf import FlaskForm
from wtforms import TextField, TextAreaField, SubmitField, validators, ValidationError
import uuid
import os.path
import webbrowser


#youtube importit
from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.tools import argparser

mail = Mail()
app = Flask(__name__)
app.secret_key = 'salainen avain'
mysql = MySQL()

#uplloadikansio	
app.config['UPLOAD_FOLDER'] = 'static/Uploads'
 
# MySQL configurations heroku
app.config['MYSQL_DATABASE_USER'] = 'USER'
app.config['MYSQL_DATABASE_PASSWORD'] = 'PASSWORD'
app.config['MYSQL_DATABASE_DB'] = 'DATABASE'
app.config['MYSQL_DATABASE_HOST'] = 'HOST'
mysql.init_app(app)

#mail konffit
app.config["MAIL_SERVER"] = "SERVER"
app.config["MAIL_PORT"] = PORT
app.config["MAIL_USE_SSL"] = True
app.config["MAIL_USERNAME"] = 'email'
app.config["MAIL_PASSWORD"] = 'password'
mail.init_app(app)

#youtube conffit
DEVELOPER_KEY = "DEVELOPERKEY"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"


pageLimit = 5

class ContactForm(FlaskForm):
  name = TextField("Nimi",  [validators.Required("Ole hyva ja tayta nimesi")])
  email = TextField("Email",  [validators.Required("Ole hyva ja tayta emailisi"), validators.Email("Email pitaa olla muotoa keke@mail.com")])
  subject = TextField("Aihe",  [validators.Required("Ole hyva ja kirjoita aiheesi")])
  message = TextAreaField("Viesti",  [validators.Required("Ole hyva ja kirjoita viesti")])
  submit = SubmitField("Laheta")
  

@app.route("/")
def main():
	return render_template("index.html")
	
		
@app.route('/showSignUp')
def showSignUp():
    return render_template('signup.html')
	
@app.route('/showSignIn')
def showSignIn():
	return render_template('signin.html')
	
@app.route('/validateLogin',methods=['POST'])
def validateLogin():
    try:
        _username = request.form['inputEmail']
        _password = request.form['inputPassword']

        # connect to mysql

        con = mysql.connect()
        cursor = con.cursor()
        cursor.callproc('sp_validateLogin',(_username,))
        data = cursor.fetchall()

        if len(data) > 0:
            if check_password_hash(str(data[0][3]),_password):
                session['user'] = data[0][0]
                return redirect('/showDashboard')
            else:
                return render_template('error.html',error = 'Wrong Email address or Password.')
        else:
            return render_template('error.html',error = 'Wrong Email address or Password.')

    except Exception as e:
        return render_template('error.html',error = str(e))
    finally:
        cursor.close()
        con.close()

		
@app.route('/userHome')
def userHome():
	if session.get('user'):
		return render_template('userHome.html')
	else:
		return render_template('error.html',error = "Sisaankirjautuminen vaadittu!")

@app.route('/logout')
def logout():
    session.pop('user',None)
    return redirect('/')
	
@app.route('/showAddWish')
def showAddWish():
    return render_template('addWish.html')
	
@app.route('/showDashboard')
def showDashboard():
    return render_template('dashboard.html')
		
@app.route('/signUp',methods=['POST','GET'])
def signUp():

    try:
        _name = request.form['inputName']
        _email = request.form['inputEmail']
        _password = request.form['inputPassword']

        # validate the received values
        if _name and _email and _password:
            
            # All Good, let's call MySQL
            
            conn = mysql.connect()
            cursor = conn.cursor()
            _hashed_password = generate_password_hash(_password)
            cursor.callproc('sp_createUser',(_name,_email,_hashed_password))
            data = cursor.fetchall()
            flash("TUNNUSLUOTU")
            

            if len(data) is 0:
                conn.commit()
                return redirect("/showSignIn")
            else:
                return json.dumps({'error':str(data[0])})
        else:
            return json.dumps({'html':'<span>Enter the required fields</span>'})

    except Exception as e:
        return json.dumps({'error':str(e)})
    finally:
        cursor.close() 
        conn.close()
		
        return redirect("/showSignIn")


@app.route('/getAllWishes')
def getAllWishes():
    try:
        if session.get('user'):
            _user = session.get('user')
            conn = mysql.connect()
            cursor = conn.cursor()
            cursor.callproc('sp_GetAllWishes',(_user,))
            result = cursor.fetchall()

            wishes_dict = []
            for wish in result:
                wish_dict = {
                        'Id': wish[0],
                        'Title': wish[1],
                        'Description': wish[2],
                        'FilePath': wish[3],
                        'Like':wish[4],
                        'HasLiked':wish[5]}
                wishes_dict.append(wish_dict)		

            return json.dumps(wishes_dict)
        else:
            return render_template('error.html', error = 'Unauthorized Access')
    except Exception as e:
        return render_template('error.html',error = str(e))	
		
@app.route('/addWish',methods=['POST'])
def addWish():
    try:
        if session.get('user'):
            _title = request.form['inputTitle']
            _description = request.form['inputDescription']
            _user = session.get('user')
            if request.form.get('filePath') is None:
                _filePath = ''
            else:
                _filePath = request.form.get('filePath')
            if request.form.get('private') is None:
                _private = 0
            else:
                _private = 1
            if request.form.get('done') is None:
                _done = 0
            else:
                _done = 1

            conn = mysql.connect()
            cursor = conn.cursor()
            cursor.callproc('sp_addWish',(_title,_description,_user,_filePath,_private,_done))
            data = cursor.fetchall()

            if len(data) is 0:
                conn.commit()
                return redirect('/userHome')
            else:
                return render_template('error.html',error = 'An error occurred!')

        else:
            return render_template('error.html',error = 'Unauthorized Access')
    except Exception as e:
        return render_template('error.html',error = str(e))
    finally:
        cursor.close()
        conn.close()


		
@app.route('/getWish',methods=['POST'])
def getWish():
    try:
        if session.get('user'):
            _user = session.get('user')
            _limit = pageLimit
            _offset = request.form['offset']
            _total_records = 0

            con = mysql.connect()
            cursor = con.cursor()
            cursor.callproc('sp_GetWishByUser',(_user,_limit,_offset,_total_records))
            
            wishes = cursor.fetchall()
            cursor.close()

            cursor = con.cursor()

            cursor.execute('SELECT @_sp_GetWishByUser_3');

            outParam = cursor.fetchall()

            response = []
            wishes_dict = []
            for wish in wishes:
                wish_dict = {
                        'Id': wish[0],
                        'Title': wish[1],
                        'Description': wish[2],
                        'Date': wish[4]}
                wishes_dict.append(wish_dict)
            response.append(wishes_dict)
            response.append({'total':outParam[0][0]}) 

            return json.dumps(response)
        else:
            return render_template('error.html', error = 'Unauthorized Access')
    except Exception as e:
        return render_template('error.html', error = str(e))

@app.route('/contacts', methods=['GET', 'POST'])
def contacts():
	session.get('user')	
	form = ContactForm()
	
	if request.method == 'POST':
		if form.validate() == False:
			flash('Kaikki kentat pitaa tayttaa')
			return render_template('contacts.html', form=form)
		else:
			msg = Message(form.subject.data, sender='contact@localhost.com', recipients=['viidakonvip@gmail.com'])
			msg.body = """
			Lahettajan nimi: %s, Sahkoposti: %s
			
			Viesti:
			
			%s
			""" % (form.name.data, form.email.data, form.message.data)
			mail.send(msg)
			
			return render_template('contacts.html', success=True)
	
	elif request.method == 'GET':	
		return render_template('contacts.html', form=form)

		
#ei sisaankirjautuneen contact
@app.route('/contact', methods=['GET', 'POST'])
def contact():
	session.get('user')	
	form = ContactForm()
	
	if request.method == 'POST':
		if form.validate() == False:
			flash('Kaikki kentat pitaa tayttaa')
			return render_template('contact.html', form=form)
		else:
			msg = Message(form.subject.data, sender='contact@localhost.com', recipients=['viidakonvip@gmail.com'])
			msg.body = """
			Lahettajan nimi: %s, Sahkoposti: %s
			
			Viesti:
			
			%s
			""" % (form.name.data, form.email.data, form.message.data)
			mail.send(msg)
			
			return render_template('contact.html', success=True)
	
	elif request.method == 'GET':	
		return render_template('contact.html', form=form)
		
#mita wishia ollaan editoimassa
@app.route('/getWishById',methods=['POST'])
def getWishById():
    try:
        if session.get('user'):
            
            _id = request.form['id']
            _user = session.get('user')
    
            conn = mysql.connect()
            cursor = conn.cursor()
            cursor.callproc('sp_GetWishById',(_id,_user))
            result = cursor.fetchall()

            wish = []
            wish.append({'Id':result[0][0],'Title':result[0][1],'Description':result[0][2],'FilePath':result[0][3],'Private':result[0][4],'Done':result[0][5]})

            return json.dumps(wish)
        else:
            return render_template('error.html', error = 'Unauthorized Access')
    except Exception as e:
        return render_template('error.html',error = str(e))

		
@app.route('/updateWish', methods=['POST'])
def updateWish():
    try:
        if session.get('user'):
            _user = session.get('user')
            _title = request.form['title']
            _description = request.form['description']
            _wish_id = request.form['id']
            _filePath = request.form['filePath']
            _isPrivate = request.form['isPrivate']
            _isDone = request.form['isDone']


            conn = mysql.connect()
            cursor = conn.cursor()
            cursor.callproc('sp_updateWish',(_title,_description,_wish_id,_user,_filePath,_isPrivate,_isDone))
            data = cursor.fetchall()

            if len(data) is 0:
                conn.commit()
                return json.dumps({'status':'OK'})
            else:
                return json.dumps({'status':'ERROR'})
    except Exception as e:
        return json.dumps({'status':'Unauthorized access'})
    finally:
        cursor.close()
        conn.close()



@app.route('/deleteWish',methods=['POST'])
def deleteWish():
    try:
        if session.get('user'):
            _id = request.form['id']
            _user = session.get('user')

            conn = mysql.connect()
            cursor = conn.cursor()
            cursor.callproc('sp_deleteWish',(_id,_user))
            result = cursor.fetchall()

            if len(result) is 0:
                conn.commit()
                return json.dumps({'status':'OK'})
            else:
                return json.dumps({'status':'An Error occured'})
        else:
            return render_template('error.html',error = 'Unauthorized Access')
    except Exception as e:
        return json.dumps({'status':str(e)})
    finally:
        cursor.close()
        conn.close()
		
@app.route('/upload', methods=['GET', 'POST'])
def upload():
	if request.method == 'POST':
		file = request.files['file']
		extension = os.path.splitext(file.filename)[1]
		f_name = str(uuid.uuid4()) + extension
		file.save(os.path.join(app.config['UPLOAD_FOLDER'], f_name))
		return json.dumps({'filename':f_name})


@app.route('/addUpdateLike',methods=['POST'])
def addUpdateLike():
    try:
        if session.get('user'):
            _wishId = request.form['wish']
            _like = request.form['like']
            _user = session.get('user')
           

            conn = mysql.connect()
            cursor = conn.cursor()
            cursor.callproc('sp_AddUpdateLikes',(_wishId,_user,_like))
            data = cursor.fetchall()
            

            if len(data) is 0:
                conn.commit()
                cursor.close()
                conn.close()

               
                conn = mysql.connect()
                cursor = conn.cursor()
                cursor.callproc('sp_getLikeStatus',(_wishId,_user))
                
                result = cursor.fetchall()		

                return json.dumps({'status':'OK','total':result[0][0],'likeStatus':result[0][1]})
            else:
                return render_template('error.html',error = 'An error occurred!')

        else:
            return render_template('error.html',error = 'Unauthorized Access')
    except Exception as e:
        return render_template('error.html',error = str(e))
    finally:
        cursor.close()
        conn.close()



@app.route("/showUtube")
def showUtube():
	return render_template("utube.html")

@app.route('/youtubeSearch', methods=["POST"])
def youtube_search():
	youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
	developerKey=DEVELOPER_KEY)

	# Call the search.list method to retrieve results matching the specified
	# query term.
	search_response = youtube.search().list(
	q=request.form['inputSearch'],
	part="id,snippet",
	maxResults=25
	).execute()

	videos = {}
	#channels = []
	#playlists = []

	# Add each result to the appropriate list, and then display the lists of
	# matching videos, channels, and playlists.
	for search_result in search_response.get("items", []):
		if search_result["id"]["kind"] == "youtube#video":
			videos[search_result["snippet"]["title"]]="https://www.youtube.com/embed/{0:.50s}".format(search_result["id"]["videoId"])
			#videos.append("%s (%s)" % (search_result["snippet"]["title"],
			#				 search_result["id"]["videoId"]))
		#elif search_result["id"]["kind"] == "youtube#channel":
		#	channels.append("%s (%s)" % (search_result["snippet"]["title"],
		#					   search_result["id"]["channelId"]))
		#elif search_result["id"]["kind"] == "youtube#playlist":
		#	playlists.append("%s (%s)" % (search_result["snippet"]["title"],
		#						search_result["id"]["playlistId"]))

								

	print ("Videos:\n", "\n".join(videos), "\n")
	#print ("Channels:\n", "\n".join(channels), "\n")
	#print ("Playlists:\n", "\n".join(playlists), "\n")

	
	return render_template("/showYoutubeList.html", videos = videos)
	try:
		youtube_search(args)
	except HttpError as e:
		print ("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))
	except TypeError:
		pass


	
if __name__ == "__main__":
	app.run()
	
