from atproto import Client,models
import os
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
    client = Client()
    if region == "kanto":
        client.login("train-kanto.f5.si", os.getenv("BLUESKY_PASS_KANTO"))
        uri = r.get("kanto_train_uri").strip('"') 
    elif region == "kansai":
        client.login("train-kansai.f5.si", os.getenv("BLUESKY_PASS_KANSAI"))
        uri = r.get("kansai_train_uri").strip('"') 

    post_data = client.get_posts([uri])
    try:
        post_text = re.search(r"text='(.*?)'", str(post_data)).group(1)
        if post_text == "運行状況に変更はありません。":
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
        root_post_ref = models.create_strong_ref(post)
      elif message_list.index(m) == 1:
        reply_to_root = models.create_strong_ref(
            client.send_post(
                text= m,
                reply_to=models.AppBskyFeedPost.ReplyRef(parent=root_post_ref,root=root_post_ref),
            )
        )
      else:
        reply_to_root = models.create_strong_ref(
            client.send_post(
                text= m,
                reply_to=models.AppBskyFeedPost.ReplyRef(parent=reply_to_root,root=root_post_ref),
            )
        )

    
    if region == "kanto":
      r.set("kanto_train_uri", post.uri)
      client.unrepost("at://did:plc:f2nbethp4g7xfdthyv2wipjo/app.bsky.feed.post/3klqfg7fbia2z")
      client.repost("at://did:plc:f2nbethp4g7xfdthyv2wipjo/app.bsky.feed.post/3klqfg7fbia2z","bafyreidpslbv6vp3ghpyw7c74s7hhkc7coylelzq24dfvyo5ghcnqgplwi")
    elif region == "kansai":
      r.set("kansai_train_uri", post.uri)
      client.unrepost("at://did:plc:hpioxwkkbmbexev43wjiti4d/app.bsky.feed.post/3klqfxniufh2s")
      client.repost("at://did:plc:hpioxwkkbmbexev43wjiti4d/app.bsky.feed.post/3klqfxniufh2s","bafyreidwie6e2qifxhcd4rketu3dsqmqf3ynshithkwtg6l54zmrvsxwjq")
    
    print(f"Blueskyに{region}の鉄道情報の投稿に成功しました")
