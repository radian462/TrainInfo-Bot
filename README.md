# 運行状況Bot
電車の運行状況を10分ごとに取得して投稿するBotです。<br>
現時点ではBlueskyのみ稼働しています。<br>
本Botは各鉄道会社とは関係ない非公式なものです。

運行状況のソースは[NHK鉄道運行情報](https://www3.nhk.or.jp/news/traffic/)をメインとし、アクセス出来ない場合のサブとして[Yahoo!路線情報](https://transit.yahoo.co.jp/diainfo)から取得します。

全く同じ状況の場合はポストされません。  
また、通常のステータスを含むステータスはそのステータスとして扱います。(例:「車両都合に伴う運転計画」→「運転計画」、「事故に伴う運転見合わせ」→「運転見合わせ」)

# アカウント
- Bluesky
  - [@train-kanto.bsky.social](https://bsky.app/profile/did:plc:f2nbethp4g7xfdthyv2wipjo)
  - [@train-kansai.bsky.social](https://bsky.app/profile/did:plc:hpioxwkkbmbexev43wjiti4d)
 
- Misskey.io
  - [@train_kanto](https://misskey.io/@train_kanto)   
  - [@train_kansai](https://misskey.io/@train_kansai)  

# クレジット
アイコンは[こちら](https://www.ac-illust.com/main/detail.php?id=1774862&wo)からお借りしました

# 要望
要望などは[Issues](https://github.com/radian462/TrainInfo-Bot/issues)にお願いします。
