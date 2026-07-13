"""
人生ラボ ビルドスクリプト
========================
content/{lab}/*.md を読み込み、以下を自動生成する:
  1. labs/{lab}/{slug}.html      … 記事詳細ページ
  2. labs/{lab}.html              … 研究所トップの記事一覧を更新
  3. sns/{slug}.txt               … SNS投稿文（X用ドラフト）

使い方:
  python3 build.py

Claude Codeへの依頼テンプレート:
  「content/{lab}/ に新しい記事(.md)を書いて、build.pyを実行して」
"""

import os
import re
import csv
import glob
import yaml
import markdown as md

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.join(ROOT, "content")
LABS_DIR = os.path.join(ROOT, "labs")
SNS_DIR = os.path.join(ROOT, "sns")

LABS = {
    "career": {"code": "LAB.01", "accent": "career", "name": "キャリア研究所",
               "eyebrow": "CAREER / DECISION-MAKING",
               "lead": "転職、昇進、異動、キャリアの分岐点で立ち止まったときに、意思決定と自己理解のための知見を集める研究所です。"},
    "ai": {"code": "LAB.02", "accent": "ai", "name": "AI研究所",
           "eyebrow": "AI / TOOLS & AUTOMATION",
           "lead": "生活と仕事にAIをどう組み込むか。ツールの選び方から使いこなし方まで、実際に試した結果を共有する研究所です。"},
    "childcare": {"code": "LAB.03", "accent": "childcare", "name": "育児研究所",
                  "eyebrow": "CHILDCARE / EVIDENCE, NOT OPINION",
                  "lead": "正解のない子育てを、記録と検証で少しずつ楽にする研究所です。年齢別の悩みと工夫を蓄積していきます。"},
    "english": {"code": "LAB.04", "accent": "english", "name": "英語研究所",
                "eyebrow": "ENGLISH / SYSTEMS OVER WILLPOWER",
                "lead": "大人になってからの英語学習を、根性論ではなく仕組みで続けるための研究所です。学習法とAI活用の実験記録を蓄積します。"},
    "money": {"code": "LAB.05", "accent": "money", "name": "お金研究所",
              "eyebrow": "MONEY / NUMBERS OVER EMOTION",
              "lead": "家計、住宅ローン、資産形成。感情論を排し、数字とライフプランで判断するための材料を集める研究所です。"},
}

# 「7つの鍵」— 5研究所とは別の思想レイヤー。ブランド記事はここに置く。
BRAND_INFO = {
    "code": "PHILOSOPHY",
    "accent": "brand",
    "name": "7つの鍵",
    "eyebrow": "THE SEVEN KEYS / PHILOSOPHY LAYER",
    "lead": "7つの鍵は、人生ラボのどの研究所にも属さない、全体を支える思想です。各研究所の記事は、この考え方と自然につながっています。",
}

ARTICLE_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} ― {lab_name} ｜ 人生ラボ</title>
<meta name="description" content="{description}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:type" content="article">
<link rel="stylesheet" href="../../style.css">
<script async src="https://www.googletagmanager.com/gtag/js?id=G-D94ZQMMMZ5"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', 'G-D94ZQMMMZ5');
</script>
</head>
<body>

<header class="site-header">
  <div class="wrap">
    <a href="../../index.html" class="wordmark">人生ラボ<small>LIFE RESEARCH LAB</small></a>
    <nav class="site-nav">
      <a href="../../index.html#labs">研究所一覧</a>
      <a href="../{lab}.html">{lab_name}</a>
    </nav>
  </div>
</header>

<div class="wrap">
  <a href="../{lab}.html" class="back-link">← {lab_name}に戻る</a>
</div>

<section class="article-page-header entry-{accent}">
  <div class="wrap">
    <p class="cat">{category}</p>
    <h1>{title}</h1>
    <div class="article-meta">
      <span>{date}</span>
      <span>{lab_name}</span>
    </div>
  </div>
</section>

<article class="wrap entry-{accent}">
  {hero_image}
  <div class="article-body">
    {body}
    {haru_comment}
    {cta_box}
    {disclosure}
  </div>
</article>

<section class="related-wrap wrap">
  <h2>{lab_name}の他の記事</h2>
  <div class="related-list">
{related}
  </div>
</section>

<footer class="site-footer">
  <div class="wrap">
    <p>© 2026 人生ラボ</p>
    <p>{code} / {lab_name}</p>
  </div>
</footer>

</body>
</html>
"""

RELATED_CARD = """    <a href="{slug}.html" class="related-card">
      <p class="cat">{category}</p>
      <h3>{title}</h3>
    </a>"""

DISCLOSURE_HTML = '<p class="disclosure">本記事にはアフィリエイトリンクを含む場合があります。商品の選定・評価は独自の基準に基づいています。</p>'

FINANCIAL_RISK_DISCLOSURE_HTML = '''<div class="disclosure disclosure-risk">
  <p><strong>広告に関する注記</strong>：本記事は金融商品・サービスに関する広告（アフィリエイト）を含みます。紹介する情報は独自の基準によるものであり、当該事業者が作成したものではありません。</p>
  <p><strong>リスクに関する注記</strong>：FXをはじめとする金融商品の取引には、為替相場・金利等の変動により元本を超える損失が生じるおそれがあります。手数料等の詳細は各事業者の公式ページでご確認ください。本記事は特定の商品の利用を推奨するものではなく、投資助言を目的としたものでもありません。</p>
</div>'''

CTA_BOX_TEMPLATE = """<div class="cta-box">
  <p class="cta-label">{label}</p>
  <p class="cta-text">{text}</p>
  <a href="{url}" class="cta-button" target="_blank" rel="noopener sponsored">{button_text}</a>
</div>"""

HARU_COMMENT_LABELS = {
    "experiment": "所長の実験メモ",
    "opinion": "所長の見解",
    "insight": "所長の気づき",
}

HARU_COMMENT_TEMPLATE = """<div class="haru-comment">
  <img class="haru-comment-avatar" src="../../assets/images/haru/avatar.jpg" alt="ハル所長">
  <div class="haru-comment-body">
    <p class="haru-comment-label">{label}</p>
    <p class="haru-comment-text">{text}</p>
  </div>
</div>"""

ABOUT_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>所長紹介 ― 人生ラボ</title>
<meta name="description" content="{description}">
<link rel="stylesheet" href="style.css">
<script async src="https://www.googletagmanager.com/gtag/js?id=G-D94ZQMMMZ5"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', 'G-D94ZQMMMZ5');
</script>
</head>
<body>

<header class="site-header">
  <div class="wrap">
    <a href="index.html" class="wordmark">人生ラボ<small>LIFE RESEARCH LAB</small></a>
    <nav class="site-nav">
      <a href="index.html#labs">研究所一覧</a>
      <a href="brand.html">7つの鍵</a>
    </nav>
  </div>
</header>

<section class="lab-header entry-brand">
  <div class="wrap">
    <a href="index.html" class="back-link">← トップに戻る</a>
    <p class="hero-eyebrow">ABOUT THE DIRECTOR</p>
    <h1>所長紹介</h1>
  </div>
</section>

<article class="wrap">
  <div class="article-body about-body">
    {body}
  </div>
</article>

<footer class="site-footer">
  <div class="wrap">
    <p>© 2026 人生ラボ</p>
    <p>ABOUT</p>
  </div>
</footer>

</body>
</html>
"""

LAB_INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} ― 人生ラボ</title>
<meta name="description" content="{lead}">
<link rel="stylesheet" href="../style.css">
<script async src="https://www.googletagmanager.com/gtag/js?id=G-D94ZQMMMZ5"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', 'G-D94ZQMMMZ5');
</script>
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
    <span class="count">{count_label}</span>
  </div>

  <div class="article-grid entry-{accent}">
{articles}
  </div>
  {placeholder}
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

ARTICLE_CARD = """    <a href="{lab}/{slug}.html" class="article-card">
      <p class="cat">{category}</p>
      <h3>{title}</h3>
      <p>{description}</p>
    </a>"""

ARTICLE_CARD = """    <a href="{lab}/{slug}.html" class="article-card">
      <p class="cat">{category}</p>
      <h3>{title}</h3>
      <p>{description}</p>
    </a>"""

# ----- 7つの鍵(ブランド記事)用テンプレート -----
# brand/{slug}.html は root から1階層下(labs/{lab}.html と同じ深さ)

BRAND_ARTICLE_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} ― 7つの鍵 ｜ 人生ラボ</title>
<meta name="description" content="{description}">
<link rel="stylesheet" href="../style.css">
<script async src="https://www.googletagmanager.com/gtag/js?id=G-D94ZQMMMZ5"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', 'G-D94ZQMMMZ5');
</script>
</head>
<body>

<header class="site-header">
  <div class="wrap">
    <a href="../index.html" class="wordmark">人生ラボ<small>LIFE RESEARCH LAB</small></a>
    <nav class="site-nav">
      <a href="../index.html#labs">研究所一覧</a>
      <a href="../brand.html">7つの鍵</a>
    </nav>
  </div>
</header>

<div class="wrap">
  <a href="../brand.html" class="back-link">← 7つの鍵に戻る</a>
</div>

<section class="article-page-header entry-brand">
  <div class="wrap">
    <p class="cat">{category}</p>
    <h1>{title}</h1>
    <div class="article-meta">
      <span>{date}</span>
      <span>7つの鍵</span>
    </div>
  </div>
</section>

<article class="wrap entry-brand">
  <div class="article-body">
    {body}
  </div>
</article>

<footer class="site-footer">
  <div class="wrap">
    <p>© 2026 人生ラボ</p>
    <p>7つの鍵</p>
  </div>
</footer>

</body>
</html>
"""

BRAND_INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>7つの鍵 ― 人生ラボ</title>
<meta name="description" content="{lead}">
<link rel="stylesheet" href="style.css">
<script async src="https://www.googletagmanager.com/gtag/js?id=G-D94ZQMMMZ5"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', 'G-D94ZQMMMZ5');
</script>
</head>
<body>

<header class="site-header">
  <div class="wrap">
    <a href="index.html" class="wordmark">人生ラボ<small>LIFE RESEARCH LAB</small></a>
    <nav class="site-nav">
      <a href="index.html#labs">研究所一覧</a>
      <a href="index.html#manifesto">この場所について</a>
    </nav>
  </div>
</header>

<section class="lab-header entry-brand">
  <div class="wrap">
    <a href="index.html" class="back-link">← トップに戻る</a>
    <p class="hero-eyebrow">PHILOSOPHY LAYER</p>
    <h1>7つの鍵</h1>
    <p>{lead}</p>
  </div>
</section>

<div class="wrap">
  <div class="section-head">
    <h2>記事一覧</h2>
    <span class="count">{count_label}</span>
  </div>

  <div class="article-grid entry-brand">
{articles}
  </div>
  {placeholder}
</div>

<footer class="site-footer">
  <div class="wrap">
    <p>© 2026 人生ラボ</p>
    <p>7つの鍵</p>
  </div>
</footer>

</body>
</html>
"""

NEW_ARTICLE_CARD = """    <a href="labs/{lab}/{slug}.html" class="new-article-card entry-{accent}">
      <p class="new-article-lab">{lab_name}</p>
      <h3>{title}</h3>
      <p class="new-article-date">{date}</p>
    </a>"""

BRAND_ARTICLE_CARD = """    <a href="brand/{slug}.html" class="article-card">
      <p class="cat">{category}</p>
      <h3>{title}</h3>
      <p>{description}</p>
    </a>"""

INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>人生ラボ ― 人生を研究する、AIライフプラットフォーム</title>
<meta name="description" content="キャリア・AI・育児・英語・お金。5つの研究所で、人生の実験と発見を積み重ねる。">
<link rel="stylesheet" href="style.css">
<script async src="https://www.googletagmanager.com/gtag/js?id=G-D94ZQMMMZ5"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', 'G-D94ZQMMMZ5');
</script>
</head>
<body>

<header class="site-header">
  <div class="wrap">
    <div class="wordmark">人生ラボ<small>LIFE RESEARCH LAB</small></div>
    <nav class="site-nav">
      <a href="#labs">研究所</a>
      <a href="#new">新着記事</a>
      <a href="#manifesto">この場所について</a>
      <a href="about.html">所長紹介</a>
    </nav>
  </div>
</header>

<section class="hero">
  <div class="wrap hero-grid">
    <div class="hero-text">
      <p class="hero-eyebrow">Est. 2026 / 5 Laboratories</p>
      <h1>人生は、<br>実験してもいい。</h1>
      <p>人生ラボは、キャリア・AI・育児・英語・お金という5つの研究所から成る、人生をより良くするための実験場です。答えを押しつけるのではなく、試して、記録して、次に活かす。そんな研究のプロセスを、日々の暮らしに。</p>
    </div>
    <div class="hero-visual" aria-hidden="true">
      <svg viewBox="0 0 260 260" xmlns="http://www.w3.org/2000/svg">
        <line class="hv-line" x1="130" y1="130" x2="130" y2="26"  stroke="#3E7A63" style="animation-delay:0.1s"/>
        <line class="hv-line" x1="130" y1="130" x2="228" y2="90"  stroke="#4C5FB0" style="animation-delay:0.25s"/>
        <line class="hv-line" x1="130" y1="130" x2="196" y2="212" stroke="#D39A3E" style="animation-delay:0.4s"/>
        <line class="hv-line" x1="130" y1="130" x2="64"  y2="212" stroke="#3C9088" style="animation-delay:0.55s"/>
        <line class="hv-line" x1="130" y1="130" x2="32"  y2="90"  stroke="#A8546A" style="animation-delay:0.7s"/>

        <circle class="hv-hub" cx="130" cy="130" r="7" fill="#2B2620"/>

        <circle class="hv-node" cx="130" cy="26"  r="13" fill="#3E7A63" style="animation-delay:1.0s"/>
        <circle class="hv-node" cx="228" cy="90"  r="13" fill="#4C5FB0" style="animation-delay:1.3s"/>
        <circle class="hv-node" cx="196" cy="212" r="13" fill="#D39A3E" style="animation-delay:1.6s"/>
        <circle class="hv-node" cx="64"  cy="212" r="13" fill="#3C9088" style="animation-delay:1.9s"/>
        <circle class="hv-node" cx="32"  cy="90"  r="13" fill="#A8546A" style="animation-delay:2.2s"/>
      </svg>
    </div>
  </div>
</section>

<section id="labs" class="wrap">
  <div class="section-head">
    <h2>研究所一覧</h2>
    <span class="count">5 LABS / ACTIVE</span>
  </div>

  <div class="catalog">
    <a href="labs/career.html" class="catalog-entry entry-career">
      <span class="entry-code">LAB.01</span>
      <div class="entry-body">
        <h3>キャリア研究所</h3>
        <p>転職、昇進、異動、キャリアの分岐点で立ち止まったときに。意思決定と自己理解のための知見を集める。</p>
        <div class="entry-tags"><span>転職</span><span>1on1</span><span>異動支援</span></div>
      </div>
      <span class="entry-arrow">→</span>
    </a>

    <a href="labs/ai.html" class="catalog-entry entry-ai">
      <span class="entry-code">LAB.02</span>
      <div class="entry-body">
        <h3>AI研究所</h3>
        <p>生活と仕事にAIをどう組み込むか。ツールの選び方から使いこなし方まで、実験結果を共有する。</p>
        <div class="entry-tags"><span>ツール比較</span><span>プロンプト</span><span>自動化</span></div>
      </div>
      <span class="entry-arrow">→</span>
    </a>

    <a href="labs/childcare.html" class="catalog-entry entry-childcare">
      <span class="entry-code">LAB.03</span>
      <div class="entry-body">
        <h3>育児研究所</h3>
        <p>正解のない子育てを、記録と検証で少しずつ楽にする。年齢別の悩みと工夫を蓄積する。</p>
        <div class="entry-tags"><span>年齢別</span><span>チェックリスト</span><span>共働き</span></div>
      </div>
      <span class="entry-arrow">→</span>
    </a>

    <a href="labs/english.html" class="catalog-entry entry-english">
      <span class="entry-code">LAB.04</span>
      <div class="entry-body">
        <h3>英語研究所</h3>
        <p>大人になってからの英語学習を、根性論ではなく仕組みで続ける。学習法とAI活用の実験記録。</p>
        <div class="entry-tags"><span>学習法</span><span>継続</span><span>AI活用</span></div>
      </div>
      <span class="entry-arrow">→</span>
    </a>

    <a href="labs/money.html" class="catalog-entry entry-money">
      <span class="entry-code">LAB.05</span>
      <div class="entry-body">
        <h3>お金研究所</h3>
        <p>家計、住宅ローン、資産形成。感情論を排して、数字とライフプランで判断するための材料集め。</p>
        <div class="entry-tags"><span>家計</span><span>住宅ローン</span><span>資産形成</span></div>
      </div>
      <span class="entry-arrow">→</span>
    </a>
  </div>
</section>

<section id="new" class="wrap">
  <div class="section-head">
    <h2>新着記事</h2>
    <span class="count">LATEST {new_count}</span>
  </div>

  <div class="new-articles-grid">
{new_articles}
  </div>
</section>

<section id="manifesto" class="wrap manifesto">
  <h2>「答え」ではなく、<br>「実験」を届ける。</h2>
  <div class="manifesto-body">
    <p>人生ラボは、断言しません。キャリアも、育児も、お金の判断も、正解は人によって違うからです。私たちがやるのは、実際に試し、記録し、うまくいったこと・いかなかったことを研究所ごとに蓄積していくこと。</p>
    <p>それぞれの研究所は独立して育ちますが、根っこは1つ。「人生をより良くする」という問いに対して、AIと一緒に、地道に実験を重ねる場所であることです。その根っこにある考え方は、<a href="brand.html">7つの鍵</a>としてまとめています。運営しているのは、<a href="about.html">こんな人</a>です。</p>
  </div>
</section>

<footer class="site-footer">
  <div class="wrap">
    <p>© 2026 人生ラボ</p>
    <p>LIFE RESEARCH LAB / 5 DEPARTMENTS ACTIVE</p>
  </div>
</footer>

</body>
</html>
"""

SNS_TEMPLATE_X = """【新着記事】{title}

{description}

#人生ラボ #{lab_name}
https://mylifejinseilab.com/labs/{lab}/{slug}.html
"""

SNS_TEMPLATE_THREADS = """{lab_name}で、ひとつ調べてみました。

{title}

{description}

続きはプロフィールのリンクから。
"""

SNS_TEMPLATE_NOTE = """# {title}

{description}

（この記事は「人生ラボ」{lab_name}に掲載したものです。全文はこちら↓）
https://mylifejinseilab.com/labs/{lab}/{slug}.html

---

{body_plain}
"""


def load_articles():
    articles_by_lab = {lab: [] for lab in LABS}
    for lab in LABS:
        lab_content_dir = os.path.join(CONTENT_DIR, lab)
        if not os.path.isdir(lab_content_dir):
            continue
        for path in sorted(glob.glob(os.path.join(lab_content_dir, "*.md"))):
            slug = os.path.splitext(os.path.basename(path))[0]
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read()
            fm_match = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.DOTALL)
            if not fm_match:
                print(f"WARN: frontmatter not found in {path}, skipping")
                continue
            meta = yaml.safe_load(fm_match.group(1))
            body_md = fm_match.group(2).strip()
            meta["slug"] = slug
            meta["body_md"] = body_md
            meta["body_html"] = md.markdown(body_md)
            articles_by_lab[lab].append(meta)
        # newest first
        articles_by_lab[lab].sort(key=lambda a: str(a.get("date", "")), reverse=True)
    return articles_by_lab


def load_brand_articles():
    """7つの鍵(ブランド記事)を content/brand/*.md から読み込む"""
    brand_dir = os.path.join(CONTENT_DIR, "brand")
    articles = []
    if not os.path.isdir(brand_dir):
        return articles
    for path in sorted(glob.glob(os.path.join(brand_dir, "*.md"))):
        slug = os.path.splitext(os.path.basename(path))[0]
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
        fm_match = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.DOTALL)
        if not fm_match:
            print(f"WARN: frontmatter not found in {path}, skipping")
            continue
        meta = yaml.safe_load(fm_match.group(1))
        body_md = fm_match.group(2).strip()
        meta["slug"] = slug
        meta["body_md"] = body_md
        meta["body_html"] = md.markdown(body_md)
        articles.append(meta)
    articles.sort(key=lambda a: str(a.get("date", "")), reverse=True)
    return articles


def build_article_pages(articles_by_lab):
    for lab, articles in articles_by_lab.items():
        info = LABS[lab]
        out_dir = os.path.join(LABS_DIR, lab)
        os.makedirs(out_dir, exist_ok=True)
        for i, a in enumerate(articles):
            others = [x for x in articles if x["slug"] != a["slug"]][:3]
            related_html = "\n".join(
                RELATED_CARD.format(slug=o["slug"], category=o.get("category", ""), title=o["title"])
                for o in others
            ) or '    <p class="placeholder-note" style="grid-column: 1/-1;">他の記事は準備中です。</p>'

            haru_text = a.get("haru_comment", "")
            if "[要確認:" in haru_text or "[要確認：" in haru_text:
                print(f"WARNING: {lab}/{a['slug']} の所長コメントに未確認のプレースホルダーが残っています。公開前に運営者の確認が必要です。")

            html = ARTICLE_TEMPLATE.format(
                title=a["title"],
                description=a.get("description", ""),
                lab=lab,
                lab_name=info["name"],
                accent=info["accent"],
                category=a.get("category", ""),
                date=a.get("date", ""),
                body=a["body_html"],
                hero_image=(
                    f'<img class="hero-image" src="../../{a["hero_image"]}" alt="{a["title"]}">'
                    if a.get("hero_image") else ""
                ),
                haru_comment=(
                    HARU_COMMENT_TEMPLATE.format(
                        label=HARU_COMMENT_LABELS.get(a.get("haru_comment_type"), "所長コメント"),
                        text=haru_text,
                    ) if haru_text else ""
                ),
                cta_box=(
                    CTA_BOX_TEMPLATE.format(
                        label=a.get("cta_label", "おすすめ"),
                        text=a.get("cta_text", ""),
                        url=a.get("cta_url", "#"),
                        button_text=a.get("cta_button_text", "詳しく見る"),
                    ) if a.get("cta_url") else ""
                ),
                disclosure=(
                    FINANCIAL_RISK_DISCLOSURE_HTML if a.get("financial_risk")
                    else DISCLOSURE_HTML if a.get("affiliate") else ""
                ),
                related=related_html,
                code=info["code"],
            )
            out_path = os.path.join(out_dir, f"{a['slug']}.html")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"generated article: labs/{lab}/{a['slug']}.html")


def build_lab_indexes(articles_by_lab):
    for lab, info in LABS.items():
        articles = articles_by_lab.get(lab, [])
        if articles:
            cards = "\n".join(
                ARTICLE_CARD.format(
                    lab=lab, slug=a["slug"], category=a.get("category", ""),
                    title=a["title"], description=a.get("description", "")
                )
                for a in articles
            )
            placeholder = ""
            count_label = f"{len(articles)} ARTICLES"
        else:
            cards = ""
            placeholder = '<p class="placeholder-note">この研究所は準備中です。記事は順次公開されます。</p>'
            count_label = "PREPARING"

        html = LAB_INDEX_TEMPLATE.format(
            name=info["name"], accent=info["accent"], code=info["code"],
            eyebrow=info["eyebrow"], lead=info["lead"],
            articles=cards, placeholder=placeholder, count_label=count_label,
        )
        out_path = os.path.join(LABS_DIR, f"{lab}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"updated index: labs/{lab}.html")


def build_brand_pages(brand_articles):
    out_dir = os.path.join(ROOT, "brand")
    os.makedirs(out_dir, exist_ok=True)
    for a in brand_articles:
        html = BRAND_ARTICLE_TEMPLATE.format(
            title=a["title"],
            description=a.get("description", ""),
            category=a.get("category", "7つの鍵"),
            date=a.get("date", ""),
            body=a["body_html"],
        )
        out_path = os.path.join(out_dir, f"{a['slug']}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"generated brand article: brand/{a['slug']}.html")


def build_brand_index(brand_articles):
    if brand_articles:
        cards = "\n".join(
            BRAND_ARTICLE_CARD.format(
                slug=a["slug"], category=a.get("category", "7つの鍵"),
                title=a["title"], description=a.get("description", "")
            )
            for a in brand_articles
        )
        placeholder = ""
        count_label = f"{len(brand_articles)} ARTICLES"
    else:
        cards = ""
        placeholder = '<p class="placeholder-note">まだ記事はありません。順次公開されます。</p>'
        count_label = "PREPARING"

    html = BRAND_INDEX_TEMPLATE.format(
        lead=BRAND_INFO["lead"], articles=cards,
        placeholder=placeholder, count_label=count_label,
    )
    out_path = os.path.join(ROOT, "brand.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("updated index: brand.html")


def build_index_page(articles_by_lab, n=6):
    # 全研究所の記事を横断し、新しい順にn件取得
    flat = []
    for lab, articles in articles_by_lab.items():
        info = LABS[lab]
        for a in articles:
            flat.append((a.get("date", ""), lab, info, a))
    flat.sort(key=lambda x: str(x[0]), reverse=True)
    latest = flat[:n]

    if latest:
        cards = "\n".join(
            NEW_ARTICLE_CARD.format(
                lab=lab, slug=a["slug"], accent=info["accent"],
                lab_name=info["name"], title=a["title"], date=a.get("date", ""),
            )
            for (_, lab, info, a) in latest
        )
    else:
        cards = '    <p class="placeholder-note" style="grid-column: 1/-1;">まだ記事がありません。</p>'

    html = INDEX_TEMPLATE.format(new_articles=cards, new_count=len(latest))
    out_path = os.path.join(ROOT, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"updated: index.html (新着記事 {len(latest)}件)")


def build_about_page():
    about_path = os.path.join(CONTENT_DIR, "about.md")
    if not os.path.exists(about_path):
        print("INFO: content/about.md が無いため about.html は生成しません")
        return
    with open(about_path, "r", encoding="utf-8") as f:
        raw = f.read()
    fm_match = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.DOTALL)
    if fm_match:
        meta = yaml.safe_load(fm_match.group(1)) or {}
        body_md = fm_match.group(2).strip()
    else:
        meta = {}
        body_md = raw.strip()

    haru_text = meta.get("haru_comment", "")
    if "[要確認:" in body_md or "[要確認：" in body_md or "[要確認:" in haru_text:
        print("WARNING: content/about.md に未確認のプレースホルダーが残っています。公開前に運営者の確認が必要です。")

    html = ABOUT_TEMPLATE.format(
        description=meta.get("description", "人生ラボ所長についてのページです。"),
        body=md.markdown(body_md),
    )
    out_path = os.path.join(ROOT, "about.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("updated: about.html")


def build_sns_drafts(articles_by_lab):
    os.makedirs(SNS_DIR, exist_ok=True)

    # 既存キューのposted状態を保持する(再ビルドで投稿済みフラグが消えないように)
    queue_path = os.path.join(ROOT, "sns_queue.csv")
    existing_posted = {}
    if os.path.exists(queue_path):
        with open(queue_path, "r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                existing_posted[row["slug"]] = row.get("posted", "FALSE")

    # 研究所ごとにキュー候補を溜める(ファイル生成はこれまで通り全記事分行う)
    entries_by_lab = {lab: [] for lab in LABS}

    for lab, articles in articles_by_lab.items():
        info = LABS[lab]
        # 投稿順は古い記事から(公開が早かったものを先に消化する)
        for a in sorted(articles, key=lambda x: str(x.get("date", ""))):
            out_dir = os.path.join(SNS_DIR, a["slug"])
            os.makedirs(out_dir, exist_ok=True)

            # note用の抜粋: 最初の段落(見出し行を除く)を取得
            paragraphs = [p.strip() for p in a["body_md"].split("\n\n") if p.strip() and not p.strip().startswith("#")]
            excerpt = paragraphs[0] if paragraphs else ""

            threads_text = SNS_TEMPLATE_THREADS.format(
                title=a["title"], description=a.get("description", ""),
                lab_name=info["name"],
            )

            variants = {
                "x.txt": SNS_TEMPLATE_X.format(
                    title=a["title"], description=a.get("description", ""),
                    lab_name=info["name"], lab=lab, slug=a["slug"],
                ),
                "threads.txt": threads_text,
                "note.txt": SNS_TEMPLATE_NOTE.format(
                    title=a["title"], description=a.get("description", ""),
                    lab_name=info["name"], lab=lab, slug=a["slug"],
                    body_plain=excerpt,
                ),
            }
            for filename, text in variants.items():
                out_path = os.path.join(out_dir, filename)
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(text)
            print(f"generated sns drafts: sns/{a['slug']}/{{x,threads,note}}.txt")

            flat_text = threads_text.strip().replace("\n", " / ")
            posted_flag = existing_posted.get(a["slug"], "FALSE")
            entries_by_lab[lab].append([a["slug"], lab, flat_text, posted_flag])

    # ラウンドロビンで並べ替え: career[0], ai[0], childcare[0], english[0], money[0], career[1], ...
    # これにより、数日分まとめてスプレッドシートに貼っても研究所が偏らない
    queue_rows = [["slug", "lab", "text", "posted"]]
    lab_order = list(LABS.keys())
    max_len = max((len(v) for v in entries_by_lab.values()), default=0)
    for i in range(max_len):
        for lab in lab_order:
            if i < len(entries_by_lab[lab]):
                queue_rows.append(entries_by_lab[lab][i])

    with open(queue_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(queue_rows)
    print(f"updated sns queue: sns_queue.csv ({len(queue_rows)-1} rows, round-robin order, posted status preserved)")


def build_sitemap(articles_by_lab, brand_articles):
    # 注意: Cloudflare Pagesは .html 付きURLを拡張子なしに308リダイレクトする。
    # 検索エンジンにはリダイレクト前ではなく正規URL(拡張子なし)を伝える。
    # この関数を編集する際は、必ずこのルールを維持すること(過去に複数回巻き戻った箇所)。
    base_url = "https://mylifejinseilab.com"
    urls = [f"{base_url}/", f"{base_url}/brand"]
    if os.path.exists(os.path.join(ROOT, "about.html")):
        urls.append(f"{base_url}/about")
    for lab in LABS:
        urls.append(f"{base_url}/labs/{lab}")
        for a in articles_by_lab.get(lab, []):
            urls.append(f"{base_url}/labs/{lab}/{a['slug']}")
    for a in brand_articles:
        urls.append(f"{base_url}/brand/{a['slug']}")

    entries = "\n".join(
        f"  <url><loc>{u}</loc></url>" for u in urls
    )
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{entries}
</urlset>
'''
    out_path = os.path.join(ROOT, "sitemap.xml")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"generated sitemap.xml ({len(urls)} urls, extension-less canonical URLs)")


if __name__ == "__main__":
    articles_by_lab = load_articles()
    brand_articles = load_brand_articles()
    build_article_pages(articles_by_lab)
    build_lab_indexes(articles_by_lab)
    build_brand_pages(brand_articles)
    build_brand_index(brand_articles)
    build_about_page()
    build_index_page(articles_by_lab)
    build_sns_drafts(articles_by_lab)
    build_sitemap(articles_by_lab, brand_articles)
    total = sum(len(v) for v in articles_by_lab.values())
    print(f"\nDone. {total} lab articles + {len(brand_articles)} brand articles processed.")
