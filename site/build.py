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

LAB_INDEX_TEMPLATE = """<!DOCTYPE html>
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

SNS_TEMPLATE_X = """【新着記事】{title}

{description}

#人生ラボ #{lab_name}
https://mylifejinseilab.com/labs/{lab}/{slug}.html
"""

SNS_TEMPLATE_THREADS = """{title}

{description}

続きはプロフィールのリンクから、人生ラボの{lab_name}で。
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


def build_sns_drafts(articles_by_lab):
    os.makedirs(SNS_DIR, exist_ok=True)

    # 既存キューのposted状態を保持する(再ビルドで投稿済みフラグが消えないように)
    queue_path = os.path.join(ROOT, "sns_queue.csv")
    existing_posted = {}
    if os.path.exists(queue_path):
        with open(queue_path, "r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                existing_posted[row["slug"]] = row.get("posted", "FALSE")

    queue_rows = [["slug", "lab", "text", "posted"]]
    for lab, articles in articles_by_lab.items():
        info = LABS[lab]
        for a in articles:
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

            # Threads自動投稿用キュー(Googleスプレッドシートに取り込む想定)
            flat_text = threads_text.strip().replace("\n", " / ")
            posted_flag = existing_posted.get(a["slug"], "FALSE")
            queue_rows.append([a["slug"], lab, flat_text, posted_flag])

    with open(queue_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(queue_rows)
    print(f"updated sns queue: sns_queue.csv ({len(queue_rows)-1} rows, posted status preserved)")


if __name__ == "__main__":
    articles_by_lab = load_articles()
    build_article_pages(articles_by_lab)
    build_lab_indexes(articles_by_lab)
    build_sns_drafts(articles_by_lab)
    total = sum(len(v) for v in articles_by_lab.values())
    print(f"\nDone. {total} articles processed.")