
from flask import Flask, session, abort, redirect, request
from google.oauth2 import id_token
from flask_restful import Api, Resource, marshal_with, fields
from flask_sqlalchemy import SQLAlchemy
from google_auth_oauthlib.flow import Flow
import os
import pathlib
from flask_restful import Resource
from flask import request
from pytube import YouTube
import urllib.parse
import cv2
from pip._vendor import cachecontrol
import google.auth.transport.requests
import requests
#o

## building app, api and data base
app = Flask(__name__)
api = Api(app)
app.secret_key = "thisisthesecret"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = SQLAlchemy(app)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' #for non https request in google authentication

## creating data tables for stroing video metadeta

class Vid_metadata(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    desc = db.Column(db.String(200) )
    channel = db.Column(db.String(200) )
    video_id = db.Column(db.String(200), unique=True)
    videon_path = db.Column(db.String(200), unique=True)
    video_length = db.Column(db.Integer)
    video_size = db.Column(db.Integer)


    def __repr__(self):
        return f"{self.video_id}"


## creat data table for user just to sotre user when it signup on our page


class Google_User_info(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    id = db.Column(db.String(200), unique=True)
    name = db.Column(db.String(200), unique=True)

    def __repr__(self):
        return f"{self.name}"




### serilizing the data 

video_data = {
    "sno": fields.Integer,
    "title": fields.String,
    "desc": fields.String,
    "channel": fields.String,
    "video_id": fields.String,
    "videon_path": fields.String,
    "video_length": fields.Integer,
    "video_size": fields.Integer,
}


user_data = {
    "sno": fields.Integer,
    "id":fields.String,
    "name": fields.String
}







def login_is_required(function):

    '''
    THIS FUNCTION ##(DECORATOR) WILL HANDLE AFTER THE LOGIN TO GET THE USER IN PROTECTED AREA OF YOUR WEB WITHOUD LOGIN USER HAS NOT ACCESS TO OPEN YOUR PROTECTED URL
    '''
    def wrapper(*args, **Kwargs):
        if "google_id" not in session:
            return abort(401)
        else:
            return function()

    return wrapper















### function to get youtube videos




class Download(Resource):

    '''
    This api is to download the youtube video at specific resolution (144p, 360p, 720p.. etc) 
    ## user has to submit the video url and path where to save the video and the resolution in which he wants to download his videos  ##
    '''


    def get(self):
        return {"datat":"hello world" }

    @marshal_with(video_data)
    def post(self):
        data = request.form
        yt =YouTube(data["url"]) ## youtube video usgin its url

        ## chekcing the resolution is available for this video or not
        if len(yt.streams.filter(res=data["resolution"], progressive=True)) == 0: 
            return "sorry this resolitoin video is not available"

        ## downloading the video and saving it to the user specific path
        yt.streams.filter(res=data["resolution"], progressive=True).first().download(data["path"]) 

        ## getting all the variable
        title = yt.title ## title of the video
        not_list = ["'", "/", ">", "<", ",", '"', "\\", "|"] ## windows will throw erroe if any items from this list is present in videos title
        for i in not_list:
            if i in title:
                title = title.replace(i,"")


        desc = yt.description ## description of the video
        channel = yt.author ## channel name of the videos
        filename = title+".mp4"  ## creating file name for the specific video
        video_path = os.path.join(data["path"],filename ) ## video path thats save on user computer

        ## for video duration using open cv to calculate videos length 
        video_cv = cv2.VideoCapture(video_path)
        frames = video_cv.get(cv2.CAP_PROP_FRAME_COUNT)
        fps = int(video_cv.get(cv2.CAP_PROP_FPS))
        duration = int(int(frames) / int(fps)) if fps != 0 else 0
        video_length = duration ## duration of the video

        video_size = os.path.getsize(video_path)  ## size of the video in bytes
        url_data = urllib.parse.urlparse(data["url"])
        query = urllib.parse.parse_qs(url_data.query)
        video_id = query["v"][0] ## getting the unique video id from the youtube video
        data = Vid_metadata(title=title, desc=desc, channel=channel, video_id=video_id, videon_path=video_path, video_length=video_length, video_size=video_size )
        ## saving the above data in the data base
        db.session.add(data)
        db.session.commit()

        return "data is saved completed"



class Vidlist(Resource):
    '''
        this api is to get the video list with two metadata filter's 1) filter it by title, 2) filter it by channel name #we can also sort data according to video length and its size#
        and in each page it will show 10 videos list
    '''
    @marshal_with(video_data)
    def get(self,page,):
        posts = Vid_metadata.query.paginate(page=page, per_page=10, error_out=True)
        return posts.items

    @marshal_with(video_data)
    def post(self,page):
        if request.method == "POST" and "title" in request.form: ## filtering it with title
            tag = request.form["tag"]
            search = "%{}%".format(tag)
            posts = Vid_metadata.query.filter(Vid_metadata.title.like(search)).paginate(page=page, per_page=10, error_out=True)

        if request.method == "POST" and "channel" in request.form: ## filtering it with channel name
            tag = request.form["channel"]
            search = "%{}%".format(tag)
            posts = Vid_metadata.query.filter(Vid_metadata.channel.like(search)).paginate(page=page, per_page=10, error_out=True)

            return posts.items




'''
##all google credential are here such as client id client secret json file
# i have created two oauth api one for login and one for signup
# having a single oauth api is creaing issus with missmatching uri 
'''

## NOTE YOU HAVE TO CREATE TWO OAUTH API IN CONSOLE.CLOUD.GOOGLE.COM AND FILL THE RESPECTIVE ID'S AND GOOGLE AUTHENTICATION WILL WORK FINE

GOOGLE_CLIENT_ID_LOGIN = "YOUR_CLIENT_ID_THAT_YOU_WILL_GET_ON_CREATING_NEW_OAUTH_API_IN_GOOGLE_CLOUDE"
GOOGLE_CLIENT_ID_SIGNUP = "YOUR_CLIENT_ID_THAT_YOU_WILL_GET_ON_CREATING_NEW_OAUTH_API_IN_GOOGLE_CLOUDE"
CLIENT_SECRET_FILE_LOGIN = os.path.join(pathlib.Path(__file__).parent, "client_secret_login.json") ## client secret file for login
CLIENT_SECRET_FILE_SIGNUP = os.path.join(pathlib.Path(__file__).parent, "client_secret_signup.json") ### client secret file for signup



## This is flow for login 
flow_login = Flow.from_client_secrets_file(
    client_secrets_file=CLIENT_SECRET_FILE_LOGIN,
    scopes = ["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri="http://127.0.0.1:8000/authorized/login"
)


## This is flow for signup
flow_signup = Flow.from_client_secrets_file(
    client_secrets_file=CLIENT_SECRET_FILE_SIGNUP,
    scopes = ["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri="http://127.0.0.1:8000/authorized/signup"
)       

        



class Login(Resource):

    '''
        This api will redirect the user to google authentication system
    '''
    def get(self):
        session["google_api"] = "test"

        authorization_url, state = flow_login.authorization_url()
        session["state"] = state
        return redirect(authorization_url)





class auth_login(Resource):
    '''
    This api will handle the user is already our user which is stored in Google_auth_user or he/she need to be signup first
    '''

    def get(self):
        flow_login.fetch_token(authorization_response=request.url)

        if session["state"] != request.args["state"]:
            abort(500)  # State does not match!

        credentials = flow_login.credentials
        request_session = requests.session()
        cached_session = cachecontrol.CacheControl(request_session)
        token_request = google.auth.transport.requests.Request(session=cached_session)

        id_info = id_token.verify_oauth2_token(
            id_token=credentials._id_token,
            request=token_request,
            audience=GOOGLE_CLIENT_ID_LOGIN)

        print(Google_User_info.query.filter_by(id=id_info.get("sub")).first())
        if Google_User_info.query.filter_by(id=id_info.get("sub")).first() is None:
            return "you are never be our user please signup first"


        session["google_id"] = id_info.get("sub")
        session["name"] = id_info.get("given_name")
        return "you are logged in as " + session["name"]


class Signup(Resource):
    '''
    This api will redirect to google authentication to choose user account 
    '''

    def get(self):
        authorization_url, state = flow_signup.authorization_url()
        session["state"] = state
        return redirect(authorization_url)

class auth_signup(Resource):

    """
    This api will handle to create new user and login them and save the created user data in Google_auth_user data table
    """

    def get(self):
        flow_signup.fetch_token(authorization_response=request.url)

        if session["state"] != request.args["state"]:
            abort(500)  # State does not match!

        credentials = flow_signup.credentials
        request_session = requests.session()
        cached_session = cachecontrol.CacheControl(request_session)
        token_request = google.auth.transport.requests.Request(session=cached_session)

        id_info = id_token.verify_oauth2_token(
            id_token=credentials._id_token,
            request=token_request,
            audience=GOOGLE_CLIENT_ID_SIGNUP)

        create_user = Google_User_info(id=id_info.get("sub"), name = id_info.get("given_name"))
        db.session.add(create_user)
        db.session.commit()

        session["id"] = id_info.get("sub")
        session["name"] = id_info.get("given_name")

        return "your id is created sucessfully now you are logged in as " + session["name"]


class Logout(Resource):

    """"
    This api will logout the user and redirect to the homepage 
    """
    def get(self):
        session.clear()
        return redirect("/")






## adding functions to the api routes
api.add_resource(Download, "/download")
api.add_resource(Vidlist, "/videos/<int:page>")
api.add_resource(Login, "/login")
api.add_resource(Signup, "/signup")
api.add_resource(auth_login, "/authorized/login")
api.add_resource(auth_signup, "/authorized/signup")
api.add_resource(Logout, "/logout")




if __name__ == '__main__':
    app.run(debug=True, port=8000)
    