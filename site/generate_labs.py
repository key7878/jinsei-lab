import os

LABS = [
    {
        "slug": "career",
        "code": "LAB.01",
        "accent": "career",
        "name": "キャリア研究所",
        "eyebrow": "CAREER / DECISION-MAKING",
        "lead": "転職、昇進、異動、キャリアの分岐点で立ち止まったときに、意思決定と自己理解のための知見を集める研究所です。",
        "articles": [
            ("転職判断", "転職すべきか迷ったら見る、判断基準の整理法", "今の不満が「会社」由来か「仕事内容」由来かを切り分ける、簡易セルフチェックを準備中。"),
            ("1on1", "1on1で何を話せばいいか分からない人へ", "上司・部下どちらの立場でも使える、1on1のアジェンダテンプレートを準備中。"),
            ("異動支援", "希望しない異動を打診されたときの初動", "感情的に反応する前に確認すべき3つのポイントを準備中。"),
            ("面接対策", "AIを使った模擬面接の設計方法", "AI面接官プロンプトのテンプレートを準備中。"),
        ],
    },
    {
        "slug": "ai",
        "code": "LAB.02",
        "accent": "ai",
        "name": "AI研究所",
        "eyebrow": "AI / TOOLS & AUTOMATION",
        "lead": "生活と仕事にAIをどう組み込むか。ツールの選び方から使いこなし方まで、実際に試した結果を共有する研究所です。",
        "articles": [
            ("ツール比較", "無料で使える生成AI、結局どれを選ぶべきか", "用途別（文章・画像・コーディング）の比較表を準備中。"),
            ("プロンプト", "毎日使えるプロンプトのテンプレート集", "コピペで使える定型プロンプト集を準備中。"),
            ("自動化", "AIで家事・雑務を自動化する第一歩", "身近な自動化事例を準備中。"),
            ("学習コスト", "AIに仕事を奪われないための学び方", "スキルの棚卸しフレームワークを準備中。"),
        ],
    },
    {
        "slug": "childcare",
        "code": "LAB.03",
        "accent": "childcare",
        "name": "育児研究所",
        "eyebrow": "CHILDCARE / EVIDENCE, NOT OPINION",
        "lead": "正解のない子育てを、記録と検証で少しずつ楽にする研究所です。年齢別の悩みと工夫を蓄積していきます。",
        "articles": [
            ("年齢別", "0〜2歳、実際に役立った工夫まとめ", "月齢別のチェックリストを準備中。"),
            ("共働き", "共働き家庭のタイムマネジメント実験", "分担表テンプレートを準備中。"),
            ("チェックリスト", "保育園入園前にやることリスト", "地域別の違いも含めたリストを準備中。"),
            ("AI活用", "育児にAIをどう使うか、試した結果", "AI育児相談の活用事例を準備中。"),
        ],
    },
    {
        "slug": "english",
        "code": "LAB.04",
        "accent": "english",
        "name": "英語研究所",
        "eyebrow": "ENGLISH / SYSTEMS OVER WILLPOWER",
        "lead": "大人になってからの英語学習を、根性論ではなく仕組みで続けるための研究所です。学習法とAI活用の実験記録を蓄積します。",
        "articles": [
            ("学習法", "続かない英語学習、仕組みで解決する", "3週間続けるための最小単位の設計法を準備中。"),
            ("AI活用", "AI英会話、実際どこまで使えるか検証", "無料・有料ツールの比較を準備中。"),
            ("継続", "忙しい社会人向け、隙間時間の使い方", "5分単位の学習メニュー例を準備中。"),
            ("ビジネス英語", "会議で使える定型表現の増やし方", "シーン別フレーズ集を準備中。"),
        ],
    },
    {
        "slug": "money",
        "code": "LAB.05",
        "accent": "money",
        "name": "お金研究所",
        "eyebrow": "MONEY / NUMBERS OVER EMOTION",
        "lead": "家計、住宅ローン、資産形成。感情論を排し、数字とライフプランで判断するための材料を集める研究所です。",
        "articles": [
            ("住宅ローン", "変動と固定、結局どちらが得なのか", "金利シナリオ別の試算例を準備中。"),
            ("家計", "家計簿が続かない人のための最小構成", "3項目だけ記録する簡易家計管理法を準備中。"),
            ("資産形成", "積立投資、始める前に知っておくこと", "リスク許容度チェックを準備中。"),
            ("ライフプラン", "教育費・老後資金、逆算の考え方", "ライフイベント別の逆算シートを準備中。"),
        ],
    },
]

TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} ― 人生ラボ</title>
<meta name="description" content="{lead}">
<link rel="stylesheet" href="../style.css">
</head>
<body>

<header class="site-header">
  <div class="wrap">
    <a href="../index.html" class="wordmark">人生ラボ<small>LIFE RESEARCH LAB</small></a>
    <nav class="site-nav">
      <a href="../index.html#labs">研究所一覧</a>
      <a href="../index.html#manifesto">この場所について</a>
    </nav>
  </div>
</header>

<section class="lab-header entry-{accent}">
  <div class="wrap">
    <a href="../index.html" class="back-link">← 研究所一覧に戻る</a>
    <p class="hero-eyebrow">{code} / {eyebrow}</p>
    <h1>{name}</h1>
    <p>{lead}</p>
  </div>
</section>

<div class="wrap">
  <div class="section-head">
    <h2>記事一覧</h2>
    <span class="count">PREPARING</span>
  </div>

  <div class="article-grid entry-{accent}">
{articles}
  </div>

  <p class="placeholder-note">この研究所は準備中です。記事は順次公開されます。</p>
</div>

<footer class="site-footer">
  <div class="wrap">
    <p>© 2026 人生ラボ</p>
    <p>{code} / {name}</p>
  </div>
</footer>

</body>
</html>
"""

ARTICLE_TEMPLATE = """    <div class="article-card">
      <p class="cat">{cat}</p>
      <h3>{title}</h3>
      <p>{desc}</p>
    </div>"""

os.makedirs("labs", exist_ok=True)

for lab in LABS:
    articles_html = "\n".join(
        ARTICLE_TEMPLATE.format(cat=cat, title=title, desc=desc)
        for cat, title, desc in lab["articles"]
    )
    html = TEMPLATE.format(
        name=lab["name"],
        lead=lab["lead"],
        accent=lab["accent"],
        code=lab["code"],
        eyebrow=lab["eyebrow"],
        articles=articles_html,
    )
    path = f"labs/{lab['slug']}.html"
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"generated: {path}")
