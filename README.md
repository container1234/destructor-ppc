# Destructor for PowerPC  
ゲームキューブ、Wii向けのチートバグ用コードを作成するスクリプト

## 特徴
- 楽にバグらせられる
- 自動でDolphinのiniファイルにコードを書き加え、有効化

## 必要なもの
- Python2
- コードを作成したいゲームのメモリダンプ

## 使い方
コマンドプロンプトなどでこのように入力してエンターキーを押すと、自動でコードが生成されてDolphinのGameSettingに追加される  
```
d-ppc.py (メモリダンプのパス) (開始アドレス) (終了アドレス) (コード個数) (オプション)
```
開始アドレスと終了アドレスは16進数で入力すること
オプションは1とか8とかにすればいい(暫定)

例  
```
d-ppc.py mem.raw 20000 300000 50 8
```

開始アドレスは0x10000くらいでいい  
終了アドレスの目安が分からない場合はDolphin Debuggerで確認するか、validrange.pyにメモリダンプを入れて表示された数字のあたりを終了アドレスにすればいい  
どちらも0x入れても入れなくても読み込めるはず  

## 注意
Dolphin起動中にも使用できるが、ゲームのプロパティが表示されているときに実行するとiniが上書きされて追記されたコードが無くなってしまうので、実行するときはプロパティのウインドウを閉じること

## TODO
- argparseを取り入れる
- Windows以外で使えるようにする

## ライセンス
The MIT License (MIT)