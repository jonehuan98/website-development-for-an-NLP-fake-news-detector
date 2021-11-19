#import Flask 
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from joblib import load
import pickle
import re
import string
import numpy as np

# Tweepy API (v1)
import tweepy
auth = tweepy.OAuthHandler("tCmMikkyQmxGhjiUhA6Magg73", "leEFx2yRZcxiFrggaZ3As50pVT0JrGpxGhGMCiZVooBpVLz6D5")
auth.set_access_token("791720150-PmveoVSvdh5GS9TK941PTU0jqNXMfoEvNaCcXy6S", "0MbJF2ImGweKudugOdDuYBdJkT0iYxyEuXKAeH9SSexMJ")
api = tweepy.API(auth)

# TwitterAPI (v2)
from TwitterAPI import TwitterAPI, TwitterOAuth, TwitterRequestError, TwitterConnectionError, TwitterPager
consumer_key= "tCmMikkyQmxGhjiUhA6Magg73"
consumer_secret= "leEFx2yRZcxiFrggaZ3As50pVT0JrGpxGhGMCiZVooBpVLz6D5"
access_token_key= "791720150-PmveoVSvdh5GS9TK941PTU0jqNXMfoEvNaCcXy6S"
access_token_secret= "0MbJF2ImGweKudugOdDuYBdJkT0iYxyEuXKAeH9SSexMJ"
apiV2 = TwitterAPI(consumer_key, consumer_secret, access_token_key, access_token_secret, api_version='2')

#create an instance of Flask
app = Flask(__name__)

# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# db = SQLAlchemy(app)


# class trainer(db.Model):
#     id = db.Column(db.Integer,primary_key=True)
#     contentDB = db.Column(db.String(300))
#     labelDB = db.Column(db.String(10))

#     def __init__(self,contentDB, labelDB):
#         self.contentDB = contentDB
#         self.labelDB = labelDB


@app.route('/', methods=['GET', 'POST'])
def hello():
    request_type_str = request.method
    if request_type_str == 'GET':
        return render_template("index.html")

    elif request_type_str =='POST':
        if "linker" in request.form:
            text = request.form["message"]
            raw = text
            if len(str(text)) < 15:
                return render_template("index.html",result="Please enter a valid Tweet link or an appropriate text statement", content=raw)
            try:
                # classification for tweet given by URL
                # get values regarding tweet from twitter API
                content, retweets, favourites, followers, verified, originUser, tweetid = getValues(text)
                
                # get embedded tweet html script
                tweetvariable = getembed(text)["html"]
                
                # predict the origin tweet
                prediction = predictions(content)

                # display result based on prediction
                display = displaySingleTweetResult(prediction)

                # super spreader score determination
                # only calculate score if tweet has misinformation
                if prediction ==0:
                    # get values regarding origin user
                    mostRecentTweets, averageFavs, averageRetweets = getMostRecent(originUser)
                    # get values regarding origin tweet replies
                    replies = getReplies(tweetid)
                    # calculate scores based on collected values
                    superSpreaderScore = getScore(mostRecentTweets, averageFavs, averageRetweets, retweets, favourites, followers, verified, replies)
                else: superSpreaderScore = ""

                return render_template("index.html",result=display,embed=tweetvariable, displayfeedback=True, score=superSpreaderScore, prediction=prediction)
            except:
                return render_template("index.html",result="Please enter a valid Tweet link or an appropriate text statement", content=raw)
        
        elif "texter" in request.form:
            text = request.form["message"]
            raw = text
            if len(str(text)) < 15:
                return render_template("index.html",result="Please enter a valid Tweet link or an appropriate text statement", content=raw)
            prediction = predictions(text)
            display = displaySingleTweetResult(prediction)
            return render_template("index.html",result=display, content=raw, displayfeedback=True)
        
        elif "fbtrue" in request.form:
            # trainTrue = trainer(contentDB=content, labelDB = "0")
            # db.session.add(trainTrue)
            # db.session.commit()
            pass
        elif "fbfake" in request.form:
            # trainFalse = trainer(contentDB=content, labelDB = "1")
            # db.session.add(trainTrue)
            # db.session.commit()            
            pass
        elif "fbidk" in request.form:
            pass
        return render_template("index.html", content="Thank you for your feedback, your response has been saved.")        
        
        
def predictions(text):
    text = inputformat(text)
    text = [text]
    model = load("model.joblib")
    vectorizer = pickle.load(open("vectorizer.pickle","rb"))
    xv_test = vectorizer.transform(text)
    predicted = model.predict(xv_test)
    return predicted

def displaySingleTweetResult(predicted):
    if predicted == 0:
        display = "\nThe tweet contains misinformation: &#9888;"
    elif predicted == 1:
        display = "\nThe tweet does not contain misinformation: &#9745;" 
    return display

def inputformat(text):
    text = text.lower()
    text = re.sub('\[.*?\]', '', text)
    text = re.sub("\\W"," ",text) 
    text = re.sub('https?://\S+|www\.\S+', '', text)
    text = re.sub('<.*?>+', '', text)
    text = re.sub('[%s]' % re.escape(string.punctuation), '', text)
    text = re.sub('\n', '', text)
    text = re.sub('\w*\d\w*', '', text)    
    return text

def getTweet(link):
    url = str(link)
    tweetid = url.split('/')[-1]
    tweet1 = api.get_status(tweetid, tweet_mode='extended')
    content = tweet1.full_text 
    return content

def getValues(link):
    url = str(link)
    tweetid = url.split('/')[-1]
    tweet1 = api.get_status(tweetid, tweet_mode='extended')
    content = tweet1.full_text

    retweets = tweet1.retweet_count
    favourites = tweet1.favorite_count
    originUser = tweet1.user.id_str
    followers = tweet1.user.followers_count
    verified = tweet1.user.verified

    tweetid = tweet1.id_str

    return content, retweets, favourites, followers, verified, originUser, tweetid

def getMostRecent(originUser):
    mostRecentTweets = []
    mostRecentFavs = []
    mostRecentRetweets= []
    recentweetobjects = api.user_timeline(user_id = str(originUser), count=10, tweet_mode="extended")
    for i in recentweetobjects:
        mostRecentTweets.append(i.full_text)
        mostRecentFavs.append(i.favorite_count)
        mostRecentRetweets.append(i.retweet_count)
    averageFavs = np.mean(mostRecentFavs)
    averageRetweets = np.mean(mostRecentRetweets)
    return mostRecentTweets, averageFavs, averageRetweets

def getReplies(tweetid):
    replies=[]
    r = apiV2.request('tweets/search/recent', {
	'query': f'conversation_id:{tweetid}',
	'tweet.fields':'text',
    'expansions':'author_id'})

    for item in r:
        if len(replies) <10:
            replies.append(item["text"])
    
    return replies

def getScore(mostRecentTweets, averageFavs, averageRetweets, retweets, favourites, followers, verified, replies):
    misinformationList = []
    for i in mostRecentTweets:
        misinformationList.append(predictions(i))
    misinformationScore = (np.sum(misinformationList == 0))/len(misinformationList)
    
    if retweets > averageRetweets:
        retweetScore = 1
    else:
        retweetScore = 0
    if favourites > averageFavs:
        favouriteScore = 1
    else:
        favouriteScore = 0
    if verified:
        verifiedScore = 1
    else:
        verifiedScore = 0
    if followers >= 707:
        followerScore = 1
    else:
        followerScore = 0
    
    engagementScore = np.mean([retweetScore,favouriteScore,verifiedScore,followerScore])

    superScoreList = [misinformationScore, engagementScore]

    influenceList = []
    # if at least one reply found
    if len(replies) > 0:
        for i in replies:
            influenceList.append(predictions(i))
        influenceScore = (np.sum(influenceList == 0))/len(influenceList)
        superScoreList.append(influenceScore)
    
    superSpreaderScore = np.mean(superScoreList)
    print(superScoreList)
    return str(round(superSpreaderScore*100, 2))

def getembed(link):
    embedurl = api.get_oembed(str(link))
    return embedurl

if __name__ == '__main__':
    # db.create_all()
    app.run(debug=True)

