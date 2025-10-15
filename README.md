# ツール集
- [コンプリート確率計算](https://tokiyui.github.io/tool/rawphoto.html): アイドルの生写真(など)のコンプリート確率を計算するツールです。
- [RealtimeMoon](https://tokiyui.github.io/tool/moon.html): 月の位置や満ち欠けの状況をリアルタイムで表示(1秒ごとに自動更新)するツールです。
- [野球の統計計算機](https://tokiyui.github.io/tool/batter.html): 各種セイバーメトリクス指標を計算するツールです。
- [ときめき♡ルーレット](https://tokiyui.github.io/tool/roulette/index.html): 超ときめき♡宣伝部の個人アー写が切り替わります。クリックで一時停止して遊ぶことができます。
- [ECMWF-AIFS初期値比較](https://tokiyui.github.io/tool/AIFS.html): AI気象モデルECMWF-AIFSの予想図を、米国の気象愛好家Ryan Maue氏が公開しているサイトから取得し、初期値比較ができるように表示しています。
- [共演イベント検索](https://tokiyui.github.io/tool/common.html): イベンターノートから、指定した2組のアーティストが共演したイベントを抽出します。
- [気象計算機](https://tokiyui.github.io/tool/metcalc.html): 露点・湿数・湿球温度・温位・相当温位・飽和相当温位を計算するツールです。
- [波高実況](https://tokiyui.github.io/tool/waveobs.html): ナウファス、船舶観測、ブイ観測、衛星観測データを重ね合わせます。
- [水蒸気流入監視](https://tokiyui.github.io/tool/pwv.html): アメダスおよびそらまめくん（大気汚染監視）の風データとGNSS可降水量を表示します。
- [予想エマグラム](https://tokiyui.github.io/tool/emagram.html): データ元はWM（察して）
- [鉛直時間断面図](https://tokiyui.github.io/Danmen/): GSM、MSM、GFS（NCEP）、IFS（ECMWF）、METFR（フランス）の東京付近の鉛直ー時間断面図
  
# 自分用 
- [リンク集（暫定）](https://tokiyui.github.io/tool/index.html): ただのリンク集です。作成中。
- [現場被りチェックページ](https://tokiyui.github.io/tool/my.html): とき宣、小倉唯、石原夏織、水瀬いのりのイベントスケジュールを同時に表示。

# Pythonツール
pythonディレクトリ以下にある各ファイルです。クリックするとダウンロードされます。

## 天文計算系
- [彗星の位置計算プログラム](https://tokiyui.github.io/tool/python/2023A3.py): 2024年秋に肉眼彗星となると予想されるTsuchinshan-ATLAS彗星の位置を出力し、日の出・日の入り時の高度方位図を作成します。
- [内惑星の位置計算プログラム](https://tokiyui.github.io/tool/python/inner_planet.py): 内惑星の日の出・日の入り時の高度方位図を作成します。
- [星食開始終了図作成](https://tokiyui.github.io/tool/python/spica.py): 星食開始終了図を作成するプログラムの例です。2024/8/10のスピカ食を計算するようになっています。
- [星食図作成](https://tokiyui.github.io/tool/python/occultation.py): 星食図を作成するプログラムの例です。2024/12/25のスピカ食を計算するようになっています。
- [日食地図作成](https://tokiyui.github.io/tool/python/eclipse.py): 日食地図を作成するプログラムの例です。2035/9/2の皆既日食を計算するようになっています。
- [日食地点予想](https://tokiyui.github.io/tool/python/eclipse_point.py): 特定地点における日食の見え方を計算するプログラムの例です。2035/9/2の皆既日食を計算するようになっています。
- [月食図作成](https://tokiyui.github.io/tool/python/moonecl.py): 月食図を作成するプログラムの例です。2025/9/7の皆既月食を計算するようになっています。

## スクレイピング系
- [ゆいかおり公式HPニュースアーカイブ取得](https://tokiyui.github.io/tool/python/yuikaori_scrap.py): 小倉唯の旧公式HPとゆいかおり公式HPのNEWSの情報をwayback machineから一括取得します。
- [イベンターノート　スクレイピングツール](https://tokiyui.github.io/tool/python/eventernote.py): イベンターノートから特定のアーティストのイベントの情報を一括取得します。
- [過去の気象データ　スクレイピングツール](https://tokiyui.github.io/tool/python/get_amedas.py): 気象庁HPの過去の気象データから任意期間の複数地点のデータを取得できます。
- [過去のMSMデータ　スクレイピングツール](https://tokiyui.github.io/tool/python/wm_msm.py): データ元はWM（察して）
