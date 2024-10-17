import atproto
import twikit
import os
import random
import re
import redis

r = redis.Redis(
  host= os.getenv("UPSTASH_HOST"),
  port= os.getenv("UPSTASH_PORT"),
  password= os.getenv("UPSTASH_PASS"),
  ssl=True,
  decode_responses=True
)

def post_bluesky(region,message):
    client = atproto.Client()
    if region == "kanto":
        client.login("train-kanto.f5.si", os.getenv("BLUESKY_PASS_KANTO"))
        uri = r.get("kanto_train_uri").strip('"') 
    elif region == "kansai":
        client.login("train-kansai.f5.si", os.getenv("BLUESKY_PASS_KANSAI"))
        uri = r.get("kansai_train_uri").strip('"') 

    post_data = client.get_posts([uri])
    try:
        post_text = re.search(r"text='(.*?)'", str(post_data)).group(1)
        if post_text == "運行状況に変更はありません。" or post_text == "":
            '''
            if message == "運行状況に変更はありません。" or message == "":
                return
            '''
            client.delete_post(uri)
    except:
        pass

    message_list = [] 
    sentence = ""
    for i in re.split(r"(?<=\n\n)", message): 
      if len(sentence) + len(i) <= 300: 
        sentence += i 
      else: 
        message_list.append(sentence) 
        sentence = i 

    message_list.append(sentence) 

    for m in message_list:
      if message_list.index(m) == 0:  
        post = client.send_post(m)
        root_post_ref = atproto.models.create_strong_ref(post)
      elif message_list.index(m) == 1:
        reply_to_root = atproto.models.create_strong_ref(
            client.send_post(
                text= m,
                reply_to=atproto.models.AppBskyFeedPost.ReplyRef(parent=root_post_ref,root=root_post_ref),
            )
        )
      else:
        reply_to_root = atproto.models.create_strong_ref(
            client.send_post(
                text= m,
                reply_to=atproto.models.AppBskyFeedPost.ReplyRef(parent=reply_to_root,root=root_post_ref),
            )
        )


    if region == "kanto":
      r.set("kanto_train_uri", post.uri)
    elif region == "kansai":
      r.set("kansai_train_uri", post.uri)

    print(f"Blueskyに{region}の鉄道情報の投稿に成功しました")


def twitter_login(region):
    client = twikit.Client('ja')
    if region == "kanto":
        if os.path.exists('cookies/kanto_cookies.json'):
            client.load_cookies('cookies/kanto_cookies.json')
        else:
            client.login(
                auth_info_1= os.getenv("KANTO_TWITTER_EMAIL"),
                auth_info_2= os.getenv("train_kanto_bot"), 
                password= os.getenv("KANTO_TWITTER_PASSWORD")
            )
        client.save_cookies('cookies/kanto_cookies.json')
        print("twitter(関東)にログインしました")
    elif region == "kansai":
        if os.path.exists('cookies/kansai_cookies.json'):
            client.load_cookies('cookies/kansai_cookies.json')
        else:
            client.login(
                auth_info_1= os.getenv("KANSAI_TWITTER_EMAIL"),
                auth_info_2= os.getenv("train_kansai_bo"), 
                password= os.getenv("KANSAI_TWITTER_PASSWORD")
            )
        client.save_cookies('cookies/kansai_cookies.json')
        print("twitter(関西)にログインしました")
    return client

def twitter_tweet(region,message):
    if region == "kanto":
        client = twitter_login(region)
        tweet_id = r.get("kanto_train_tweet_id")
    elif region == "kansai":
        client = twitter_login(region)
        tweet_id = r.get("kansai_train_tweet_id")

    try:
        tweet = client.get_tweet_by_id(tweet_id)
        tweet_text = tweet.text
        if tweet_text in "運行状況に変更はありません。" or tweet_text == "":
            '''
            if message in "運行状況に変更はありません。" or message == "":
                return
            '''
            tweet.delete()
    except:
        pass


    message_list = [] 
    sentence = ""
    for i in re.split(r"(?<=\n\n)", message): 
      if len(sentence) + len(i) < 140: 
        sentence += i 
      else: 
        message_list.append(sentence) 
        sentence = i 

    message_list.append(sentence) 

    tweet = None
    for index, m in enumerate(message_list):
        retries = 5
        while retries > 0:
            try:
                if index == 0:
                    tweet = client.create_tweet(m) 
                    if region == "kanto":
                        r.set("kanto_train_tweet_id", tweet.id)
                    elif region == "kansai":
                        r.set("kansai_train_tweet_id", tweet.id)
                    print(f"{index + 1}回目の投稿に成功しました")
                else:
                    tweet = client.create_tweet(m, None, None, tweet.id)
                    print(f"{index + 1}回目の投稿に成功しました")
                break  
            except twikit.errors.DuplicateTweet:
                #参考 https://tech-blog.s-yoshiki.com/entry/303
                blank_list = ("\u0020", "\u3164", "\u00A0", "\u00AD", "\u034F",
                              "\u061C", "\u2000", "\u2001", "\u2002", "\u2003",
                              "\u2004", "\u2005", "\u2006", "\u2007", "\u2008", 
                              "\u2009")
                m = m + random.choice(blank_list)
                retries -= 1
        else:
            print(f"{index + 1}回目の投稿に失敗しました")
            break

    print(f"Twitterに{region}の鉄道情報の投稿に成功しました")
