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
import hashlib
import html as html_mod
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
               "lead": "現役の人事として、これまでキャリア相談2,000件超、採用面接1,000件超に携わってきました。昇格、異動、退職の意思決定の現場にも数多く立ち会ってきた経験から、キャリアの分岐点で使える意思決定と自己理解の知見を届ける研究所です。",
               "name_policy": '\n    <p class="lab-name-policy">現役の人事だからこそ、実名は明かせません。勤務先や当事者が特定されれば、ここで書けることの多くは書けなくなってしまうからです。だからこそ、利害関係を気にせず、人事目線の本音をそのまま届けられる場所にしたいと考えています。</p>',
               "consult_cta": '''
<section class="clab-section clab-section-tight">
  <div class="wrap">
    <div class="clab-consult">
      <p class="clab-eyebrow">Consultation</p>
      <h2 class="clab-consult-h">個別の相談について</h2>
      <p class="clab-consult-p">今のモヤモヤ、まずは気軽に聞かせてください。転職、昇格、異動、退職。人事目線での壁打ち相手として、Threads DMで相談を受け付けています。</p>
      <a href="https://www.threads.net/@mylifejinseilab" class="clab-link-brass" target="_blank" rel="noopener">Threadsで相談してみる <span class="clab-arw">→</span></a>
    </div>
  </div>
</section>''',
               "diagnostic_cta": '''
    <div class="clab-tool">
      <span class="clab-tool-verb">Use ｜ 触る</span>
      <p class="clab-tool-label">所長の研究ツール</p>
      <h2 class="clab-tool-title">見えない評価ギャップ診断</h2>
      <p class="clab-tool-text">「評価されている」と自分が思っている項目と、人事が実際に見ている項目は、たいてい一致しません。そのズレがどこにあるかを、12の質問で切り分けます。</p>
      <a href="/labs/career-diagnosis" class="clab-btn" data-ga="career_page_diagnosis">3分で診断する <span class="clab-arw">→</span></a>
    </div>''',
               "diag_flow_cta": '''
<section class="clab-section">
  <div class="wrap">
    <div class="clab-section-head">
      <p class="clab-eyebrow">After the test</p>
      <h2 class="clab-h2">診断のあとに起きること</h2>
    </div>
    <ol class="clab-flow">
      <li>
        <span class="clab-flow-n">01</span>
        <div>
          <h3>その場で結果が出る</h3>
          <p>メール登録なしで、ズレの出ている領域とその理由まで表示します。</p>
        </div>
      </li>
      <li>
        <span class="clab-flow-n">02</span>
        <div>
          <h3>詳細版を受け取る</h3>
          <p>領域ごとの改善の順序と、実際の判断でよく見られた事例をメールで送ります。</p>
        </div>
      </li>
      <li>
        <span class="clab-flow-n">03</span>
        <div>
          <h3>個別に相談する</h3>
          <p>12問で出ない部分は、その人の状況を聞かないと分かりません。DMで受けています。</p>
        </div>
      </li>
    </ol>
  </div>
</section>''',
               "note_series_cta": '''
<section class="clab-section clab-section-tight">
  <div class="wrap">
    <div class="clab-series">
      <p class="clab-eyebrow clab-eyebrow-d">Series</p>
      <h2 class="clab-series-h">人事の現場から</h2>
      <p class="clab-series-p">実際の判断の場で何が起きているかを、連載として書いています。サイトには書ききれない部分はこちらに。</p>
      <a class="clab-link-brass" href="https://note.com/key7life" target="_blank" rel="noopener">note で読む <span class="clab-arw">→</span></a>
    </div>
  </div>
</section>''',
               "director_cta": '''
<section class="clab-section clab-section-tight">
  <div class="wrap">
    <a href="../about.html" class="clab-director-link">所長について <span class="clab-arw">→</span> 詳しくはこちら</a>
  </div>
</section>'''},
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
<link rel="icon" href="../../favicon.ico" sizes="any">
<link rel="icon" href="../../favicon.svg" type="image/svg+xml">
<link rel="icon" href="../../favicon-48.png" type="image/png" sizes="48x48">
<link rel="icon" href="../../favicon-192.png" type="image/png" sizes="192x192">
<link rel="apple-touch-icon" href="../../apple-touch-icon.png">
<meta property="og:site_name" content="人生ラボ">
<meta property="og:locale" content="ja_JP">
<meta property="og:image" content="https://mylifejinseilab.com/assets/images/og-default.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
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
  <h2>関連する研究レポート</h2>
  <div class="related-list">
{related}
  </div>
</section>

<section class="follow-haru wrap">
  <div class="follow-haru-inner">
    <img class="follow-haru-avatar" src="../../assets/images/haru/avatar.jpg" alt="ハル所長">
    <div class="follow-haru-body">
      <p class="follow-haru-label">この記事が参考になったら</p>
      <p class="follow-haru-text">ハル所長をフォローすると、研究所の日々の発見が届きます。</p>
      <div class="follow-links">
        <a href="https://www.threads.com/@mylifejinseilab" target="_blank" rel="noopener" class="follow-link">Threadsでフォロー</a>
        <a href="https://note.com/key7life" target="_blank" rel="noopener" class="follow-link">noteを読む</a>
      </div>
    </div>
  </div>
</section>
{ga_events}
<footer class="site-footer">
  <div class="wrap">
    <p>© 2026 人生ラボ</p>
    <p>{code} / {lab_name}</p>
  </div>
</footer>

</body>
</html>
"""

RELATED_CARD = """    <a href="{href}" class="related-card entry-{accent}" data-ga="related_article">
      <p class="cat">{cat_label}</p>
      <h3>{title}</h3>
    </a>"""


GA_EVENTS_SNIPPET = """<script>
// 内部リンクのクリックをGA4に送る。GA4は内部リンクを自動計測しないため、
// data-ga を付けた導線だけを対象に、どの枠が押されたかを記録する。
document.addEventListener('click', function (e) {
  var el = e.target.closest('[data-ga]');
  if (!el || typeof gtag !== 'function') return;
  gtag('event', 'internal_link_click', {
    link_slot: el.getAttribute('data-ga'),
    link_url: el.getAttribute('href') || '',
    link_text: (el.textContent || '').trim().slice(0, 100)
  });
});
</script>
"""

DISCLOSURE_HTML = '<p class="disclosure">本記事にはアフィリエイトリンクを含む場合があります。商品の選定・評価は独自の基準に基づいています。</p>'

FINANCIAL_RISK_DISCLOSURE_HTML = '''<div class="disclosure disclosure-risk">
  <p><strong>広告に関する注記</strong>：本記事は金融商品・サービスに関する広告（アフィリエイト）を含みます。紹介する情報は独自の基準によるものであり、当該事業者が作成したものではありません。</p>
  <p><strong>リスクに関する注記</strong>：FXをはじめとする金融商品の取引には、為替相場・金利等の変動により元本を超える損失が生じるおそれがあります。手数料等の詳細は各事業者の公式ページでご確認ください。本記事は特定の商品の利用を推奨するものではなく、投資助言を目的としたものでもありません。</p>
</div>'''

CTA_BOX_TEMPLATE = """<div class="cta-box">
  <p class="cta-label">{label}</p>
  <p class="cta-text">{text}</p>
  <a href="{url}" class="cta-button" target="_blank" rel="noopener sponsored">{button_text}</a>{banner}
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
<meta property="og:title" content="所長紹介 ｜ 人生ラボ">
<meta property="og:description" content="{description}">
<meta property="og:type" content="profile">
<link rel="icon" href="favicon.ico" sizes="any">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="icon" href="favicon-48.png" type="image/png" sizes="48x48">
<link rel="icon" href="favicon-192.png" type="image/png" sizes="192x192">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<meta property="og:site_name" content="人生ラボ">
<meta property="og:locale" content="ja_JP">
<meta property="og:image" content="https://mylifejinseilab.com/assets/images/og-default.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
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
<meta property="og:title" content="{name} ｜ 人生ラボ">
<meta property="og:description" content="{lead}">
<meta property="og:type" content="website">
<link rel="icon" href="../favicon.ico" sizes="any">
<link rel="icon" href="../favicon.svg" type="image/svg+xml">
<link rel="icon" href="../favicon-48.png" type="image/png" sizes="48x48">
<link rel="icon" href="../favicon-192.png" type="image/png" sizes="192x192">
<link rel="apple-touch-icon" href="../apple-touch-icon.png">
<meta property="og:site_name" content="人生ラボ">
<meta property="og:locale" content="ja_JP">
<meta property="og:image" content="https://mylifejinseilab.com/assets/images/og-default.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
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
    <p>{lead}</p>{name_policy}{diagnostic_cta}{lab_panel}
  </div>
</section>
{diag_flow_cta}{lab_feature}
<div class="wrap">
  <div class="section-head">
    <h2>記事一覧</h2>
    <span class="count">{count_label}</span>
  </div>

  {article_section}
</div>
{note_series_cta}{consult_cta}{director_cta}
{ga_events}
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

# career研究所のみ「研究レポート」を2群(採用・面接 / その他)に分けて表示する。
# 運営者確定分のみ(2026-08-11時点)。新規記事追加時はここに追記が必要。
CAREER_HIRING_INTERVIEW_SLUGS = {
    "interview-rejection-common-habit",
    "interview-reverse-questions",
    "nursing-care-job-interview-motivation",
    "resignation-reason-how-to-explain-interview",
    "remote-job-interview-what-is-actually-asked",
    "reference-check-what-to-expect",
    "resume-screening-basics",
    "consulting-firm-transfer-preparation",
    "salary-negotiation-interviewer-perspective",
}

CLAB_REPORT_ITEM = """      <li><a href="{lab}/{slug}.html"><span class="clab-r-date">{date}</span><p class="clab-r-title">{title}</p></a></li>"""

CLAB_REPORT_GROUP = """    <div class="clab-report-group">
      <h3 class="clab-group-h">{group_name}</h3>
      <ul class="clab-reports">
{items}
      </ul>
    </div>"""

# ----- 7つの鍵(ブランド記事)用テンプレート -----
# brand/{slug}.html は root から1階層下(labs/{lab}.html と同じ深さ)

BRAND_ARTICLE_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} ― 7つの鍵 ｜ 人生ラボ</title>
<meta name="description" content="{description}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:type" content="article">
<link rel="icon" href="../favicon.ico" sizes="any">
<link rel="icon" href="../favicon.svg" type="image/svg+xml">
<link rel="icon" href="../favicon-48.png" type="image/png" sizes="48x48">
<link rel="icon" href="../favicon-192.png" type="image/png" sizes="192x192">
<link rel="apple-touch-icon" href="../apple-touch-icon.png">
<meta property="og:site_name" content="人生ラボ">
<meta property="og:locale" content="ja_JP">
<meta property="og:image" content="https://mylifejinseilab.com/assets/images/og-default.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
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
<meta property="og:title" content="7つの鍵 ｜ 人生ラボ">
<meta property="og:description" content="{lead}">
<meta property="og:type" content="website">
<link rel="icon" href="favicon.ico" sizes="any">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="icon" href="favicon-48.png" type="image/png" sizes="48x48">
<link rel="icon" href="favicon-192.png" type="image/png" sizes="192x192">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<meta property="og:site_name" content="人生ラボ">
<meta property="og:locale" content="ja_JP">
<meta property="og:image" content="https://mylifejinseilab.com/assets/images/og-default.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
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
  <div class="follow-haru-inner" style="margin-bottom: 8px;">
    <img class="follow-haru-avatar" src="assets/images/haru/avatar.jpg" alt="ハル所長">
    <div class="follow-haru-body">
      <p class="follow-haru-label">物語の全編はnoteで</p>
      <p class="follow-haru-text">「ふかふかな人生の7つの鍵」として、ハル所長がnoteで連載しています。</p>
      <div class="follow-links">
        <a href="https://note.com/key7life" target="_blank" rel="noopener" class="follow-link">noteで読む</a>
      </div>
    </div>
  </div>
</div>

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

# ----- トップページ(index.html)用テンプレート -----
# 回遊設計: 研究所カードに実記事タイトルを直接載せ、着地時点でクリック可能な
# 記事リンクを増やす。数値は全て content/{lab}/*.md の実数から算出する
# (仮の数値・架空の指標は出さない)。

# 研究所カードの説明文・タグは、旧 catalog-entry の文言をそのまま維持する。
INDEX_LAB_META = {
    "career":    {"desc": "転職、昇進、異動、キャリアの分岐点で立ち止まったときに。意思決定と自己理解のための知見を集める。",
                  "tags": ["転職", "1on1", "異動支援"], "tool": "1"},
    "ai":        {"desc": "生活と仕事にAIをどう組み込むか。ツールの選び方から使いこなし方まで、実験結果を共有する。",
                  "tags": ["ツール比較", "プロンプト", "自動化"], "tool": "準備中"},
    "childcare": {"desc": "正解のない子育てを、記録と検証で少しずつ楽にする。年齢別の悩みと工夫を蓄積する。",
                  "tags": ["年齢別", "チェックリスト", "共働き"], "tool": "準備中"},
    "english":   {"desc": "大人になってからの英語学習を、根性論ではなく仕組みで続ける。学習法とAI活用の実験記録。",
                  "tags": ["学習法", "継続", "AI活用"], "tool": "準備中"},
    "money":     {"desc": "家計、住宅ローン、資産形成。感情論を排して、数字とライフプランで判断するための材料集め。",
                  "tags": ["家計", "住宅ローン", "資産形成"], "tool": "準備中"},
}

IDX_LAB_ARTICLE = """          <li><a href="labs/{lab}/{slug}.html" data-ga="top_lab_article">{title}</a></li>"""

IDX_LAB_BLOCK = """      <div class="idx-lab entry-{accent}">
        <div class="idx-lab-head">
          <span class="idx-lab-code">{code}</span>
          <h3 class="idx-lab-name"><a href="labs/{lab}.html" data-ga="top_lab_name">{name}</a></h3>
          <p class="idx-lab-desc">{desc}</p>
          <div class="idx-lab-tags">{tags}</div>
          <ul class="idx-spec">
            <li><span class="k">ツール</span><span class="v">{tool}</span></li>
            <li><span class="k">レポート</span><span class="v">{count}</span></li>
          </ul>
        </div>
        <ul class="idx-lab-articles">
{articles}
        </ul>
        <a class="idx-lab-more" href="labs/{lab}.html" data-ga="top_lab_more">{name}の記事一覧（{count}件） <span class="idx-arw">→</span></a>
      </div>"""

IDX_REPORT_ITEM = """      <li><a href="labs/{lab}/{slug}.html" data-ga="top_latest">
        <div class="idx-r-meta"><span class="idx-r-lab">{lab_name}</span><span class="idx-r-date">{date}</span></div>
        <p class="idx-r-title">{title}</p>
      </a></li>"""

# ----- 英語研究所(学習ログ)用テンプレート -----
# 数値は data/english_log.yaml の実データからのみ算出する。

ELAB_PANEL = """
    <div class="elab-panel">
      <div class="elab-panel-top">
        <p class="elab-panel-title">所長の現在地</p>
        <span class="elab-badge">{current} → {target}</span>
      </div>
      <div class="elab-cells">
        <div class="elab-cell">
          <span class="k">記録した単語</span>
          <span class="v">{words}<small>語</small></span>
        </div>
        <div class="elab-cell">
          <span class="k">記録したフレーズ</span>
          <span class="v">{phrases}<small>件</small></span>
        </div>
        <div class="elab-cell">
          <span class="k">学習時間</span>
          <span class="v">{hours}<small>時間</small></span>
        </div>
        <div class="elab-cell">
          <span class="k">記録した日数</span>
          <span class="v">{days}<small>日</small></span>
        </div>
      </div>
    </div>"""

ELAB_BAR = """        <div class="elab-bar-row">
          <div class="elab-bar-head">
            <span class="elab-bar-label">{label}</span>
            <span class="elab-bar-num">{done} <span class="elab-bar-goal">/ {goal}</span></span>
          </div>
          <div class="elab-bar-track"><div class="elab-bar-fill" style="width: {pct}%"></div></div>
          <p class="elab-bar-note">{note}</p>
        </div>"""

ELAB_ENTRY = """          <li class="elab-entry" data-type="{type}" data-date="{date}" data-term="{term_key}" data-search="{search_key}">
            <div class="elab-entry-head">
              <span class="elab-entry-type elab-type-{type}">{type_label}</span>
              <span class="elab-entry-date">{date}</span>
            </div>
            <p class="elab-term">{term}</p>
            <p class="elab-meaning">{meaning}</p>
            <p class="elab-example">{example}</p>{situation}
          </li>"""

ELAB_SITUATION = """
            <p class="elab-situation"><span class="elab-situation-k">使いたかった場面</span>{situation}</p>"""

ELAB_FEATURE = """
<section class="elab-section">
  <div class="wrap">
    <div class="elab-section-head">
      <p class="elab-eyebrow">Progress to C1</p>
      <h2 class="elab-h2">C1までの距離</h2>
      <p class="elab-sub">C1到達の目安とされる語彙3,000語・フレーズ3,000件・学習500〜800時間に対して、今どこにいるか。数字は記録した分だけ動きます。</p>
    </div>
    <div class="elab-bars">
{bars}
    </div>
  </div>
</section>

<section class="elab-section elab-section-tight">
  <div class="wrap">
    <div class="elab-section-head">
      <p class="elab-eyebrow">Daily log</p>
      <h2 class="elab-h2">拾った単語・フレーズ</h2>
      <p class="elab-sub">その日に学んだ表現と、それを「使いたかったのに出てこなかった場面」を並べています。覚えた単語より、詰まった場面のほうが記録として価値があると考えています。</p>
    </div>
{controls}
{log_body}
  </div>
</section>
{script}"""

ELAB_CONTROLS = """    <div class="elab-tools">
      <div class="elab-search-wrap">
        <input type="search" id="elabSearch" class="elab-search" placeholder="単語・意味・例文・場面から探す" aria-label="単語・フレーズを検索">
      </div>
      <div class="elab-filters">
        <div class="elab-seg" role="group" aria-label="種別で絞り込む">
          <button type="button" class="elab-seg-btn is-on" data-filter="all">すべて</button>
          <button type="button" class="elab-seg-btn" data-filter="word">単語</button>
          <button type="button" class="elab-seg-btn" data-filter="phrase">フレーズ</button>
        </div>
        <select id="elabSort" class="elab-sort" aria-label="並び替え">
          <option value="new">新しい順</option>
          <option value="old">古い順</option>
          <option value="az">アルファベット順</option>
        </select>
      </div>
      <p class="elab-count" id="elabCount"></p>
    </div>"""

# 検索・絞り込み・並び替え・段階表示。件数が増えても目的の1件に辿り着けるようにする。
# 並び順の変更は保存しない(リロードで新しい順に戻る)。
ELAB_SCRIPT = """<script>
(function () {
  var list = document.getElementById('elabEntries');
  if (!list) return;
  var search = document.getElementById('elabSearch');
  var sortSel = document.getElementById('elabSort');
  var countEl = document.getElementById('elabCount');
  var moreBtn = document.getElementById('elabMore');
  var segBtns = Array.prototype.slice.call(document.querySelectorAll('.elab-seg-btn'));
  var all = Array.prototype.slice.call(list.children);
  var STEP = 24;
  var shown = STEP;
  var typeFilter = 'all';

  function matched() {
    var q = (search.value || '').trim().toLowerCase();
    return all.filter(function (el) {
      if (typeFilter !== 'all' && el.dataset.type !== typeFilter) return false;
      if (!q) return true;
      return el.dataset.search.indexOf(q) !== -1;
    });
  }

  function sorted(items) {
    var mode = sortSel.value;
    var arr = items.slice();
    if (mode === 'az') {
      arr.sort(function (a, b) { return a.dataset.term.localeCompare(b.dataset.term); });
    } else {
      arr.sort(function (a, b) {
        if (a.dataset.date === b.dataset.date) return 0;
        return a.dataset.date < b.dataset.date ? -1 : 1;
      });
      if (mode === 'new') arr.reverse();
    }
    return arr;
  }

  function render() {
    var items = sorted(matched());
    all.forEach(function (el) { el.hidden = true; });
    items.slice(0, shown).forEach(function (el) {
      el.hidden = false;
      list.appendChild(el);  // 並び替えを実DOMに反映
    });
    countEl.textContent = items.length === all.length
      ? all.length + '件'
      : items.length + '件 / 全' + all.length + '件';
    if (moreBtn) {
      var rest = items.length - shown;
      moreBtn.hidden = rest <= 0;
      moreBtn.textContent = 'もっと見る（残り' + (rest > 0 ? rest : 0) + '件）';
    }
    if (items.length === 0) {
      list.setAttribute('data-empty', '該当する記録はありません');
    } else {
      list.removeAttribute('data-empty');
    }
  }

  search.addEventListener('input', function () { shown = STEP; render(); });
  sortSel.addEventListener('change', function () { shown = STEP; render(); });
  segBtns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      segBtns.forEach(function (b) { b.classList.remove('is-on'); });
      btn.classList.add('is-on');
      typeFilter = btn.dataset.filter;
      shown = STEP;
      render();
    });
  });
  if (moreBtn) {
    moreBtn.addEventListener('click', function () { shown += STEP; render(); });
  }

  render();
})();
</script>"""

ELAB_EMPTY = """    <p class="elab-empty">記録はこれから始まります。学んだ単語・フレーズと、それを使いたかった場面を、日ごとにここへ積み上げていきます。</p>"""

# トップページのヒーロー2枚目(FOLLOW)。英語ログの実データがある場合のみ出す。
IDX_FOLLOW_CARD = """      <a class="idx-hero-follow" href="labs/english.html" data-ga="top_hero_english">
        <span class="idx-badge">研究中</span>
        <span class="idx-verb idx-verb-follow">Follow ｜ 追う</span>
        <h2 class="idx-follow-title">所長の英語やり直し研究</h2>
        <p class="idx-follow-text">B2からC1へ。学んだ単語・フレーズと、それを使いたかった場面を毎日記録しています。</p>
        <span class="idx-link-brass">この実験を追う <span class="idx-arw">→</span></span>
        <ul class="idx-spec idx-spec-dark">
          <li><span class="k">分類</span><span class="v">英語研究所</span></li>
          <li><span class="k">記録</span><span class="v">Day {days}</span></li>
          <li><span class="k">語彙・フレーズ</span><span class="v">{items}</span></li>
        </ul>
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
<title>人生ラボ ― キャリア・AI・育児・英語・お金の研究所</title>
<meta name="description" content="キャリア・AI・育児・英語・お金。5つの研究所で、人生の実験と発見を積み重ねる。">
<meta property="og:title" content="人生ラボ ― キャリア・AI・育児・英語・お金の研究所">
<meta property="og:description" content="キャリア・AI・育児・英語・お金。5つの研究所で、人生の実験と発見を積み重ねる。">
<meta property="og:type" content="website">
<meta property="og:url" content="https://mylifejinseilab.com/">
<link rel="icon" href="favicon.ico" sizes="any">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="icon" href="favicon-48.png" type="image/png" sizes="48x48">
<link rel="icon" href="favicon-192.png" type="image/png" sizes="192x192">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<meta property="og:site_name" content="人生ラボ">
<meta property="og:locale" content="ja_JP">
<meta property="og:image" content="https://mylifejinseilab.com/assets/images/og-default.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
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

<header class="site-header idx-header">
  <div class="wrap">
    <div class="wordmark">人生ラボ<small>LIFE RESEARCH LAB</small></div>
    <nav class="site-nav idx-nav">
      <a href="labs/career-diagnosis">診断ツール</a>
      <a href="#labs">研究所</a>
      <a href="#new">新着記事</a>
      <a href="#manifesto">この場所について</a>
      <a href="about.html">所長紹介</a>
      <a href="specialpage_1/">ワンキャリア転職</a>
    </nav>
  </div>
</header>

<section class="idx-bench">
  <div class="wrap idx-bench-grid">
    <div class="idx-bench-text">
      <p class="idx-eyebrow">Est. 2026 / 5 Laboratories</p>
      <h1>人生は、<br>実験してもいい。</h1>
      <p class="idx-bench-lede">人生ラボは、キャリア・AI・育児・英語・お金という5つの研究所から成る、人生をより良くするための実験場です。答えを押しつけるのではなく、試して、記録して、次に活かす。そんな研究のプロセスを、日々の暮らしに。</p>
    </div>
    <div class="idx-bench-visual" aria-hidden="true">
      <svg viewBox="0 0 260 260" xmlns="http://www.w3.org/2000/svg">
        <line class="hv-line" x1="130" y1="130" x2="130" y2="26"  stroke="#3E7A63" style="animation-delay:0.1s"/>
        <line class="hv-line" x1="130" y1="130" x2="228" y2="90"  stroke="#4C5FB0" style="animation-delay:0.25s"/>
        <line class="hv-line" x1="130" y1="130" x2="196" y2="212" stroke="#D39A3E" style="animation-delay:0.4s"/>
        <line class="hv-line" x1="130" y1="130" x2="64"  y2="212" stroke="#3C9088" style="animation-delay:0.55s"/>
        <line class="hv-line" x1="130" y1="130" x2="32"  y2="90"  stroke="#A8546A" style="animation-delay:0.7s"/>

        <circle class="hv-hub" cx="130" cy="130" r="7" fill="#EDF0F4"/>

        <circle class="hv-node" cx="130" cy="26"  r="13" fill="#3E7A63" style="animation-delay:1.0s"/>
        <circle class="hv-node" cx="228" cy="90"  r="13" fill="#4C5FB0" style="animation-delay:1.3s"/>
        <circle class="hv-node" cx="196" cy="212" r="13" fill="#D39A3E" style="animation-delay:1.6s"/>
        <circle class="hv-node" cx="64"  cy="212" r="13" fill="#3C9088" style="animation-delay:1.9s"/>
        <circle class="hv-node" cx="32"  cy="90"  r="13" fill="#A8546A" style="animation-delay:2.2s"/>
      </svg>
    </div>
  </div>

  <div class="wrap">
    <div class="idx-heroes">
      <a class="idx-hero-use" href="labs/career-diagnosis" data-ga="top_hero_diagnosis">
        <span class="idx-verb">Use ｜ 触る</span>
        <h2 class="idx-hero-title">見えない評価ギャップ診断</h2>
        <p class="idx-hero-text">「評価されている」と自分が思っている項目と、人事が実際に見ている項目は、たいてい一致しません。そのズレがどこにあるかを、12の質問で切り分けます。</p>
        <span class="idx-btn">3分で診断する <span class="idx-arw">→</span></span>
        <ul class="idx-spec idx-spec-light">
          <li><span class="k">分類</span><span class="v">キャリア研究所</span></li>
          <li><span class="k">状態</span><span class="v">公開中</span></li>
          <li><span class="k">設問</span><span class="v">全12問</span></li>
          <li><span class="k">登録</span><span class="v">不要</span></li>
        </ul>
      </a>
{follow_card}
    </div>
  </div>
</section>

<section id="labs" class="idx-section">
  <div class="wrap">
    <div class="idx-section-head">
      <p class="idx-eyebrow-light">Laboratories</p>
      <h2 class="idx-h2">5つの研究所</h2>
      <p class="idx-sub">仕事、お金、育児、AI、英語。生活のなかで実験できるものを、分けて置いています。</p>
    </div>

    <div class="idx-labs">
{lab_blocks}
    </div>
  </div>
</section>

<section id="new" class="idx-section idx-section-tight">
  <div class="wrap">
    <div class="idx-section-head">
      <p class="idx-eyebrow-light">Latest</p>
      <h2 class="idx-h2">新着記事</h2>
      <p class="idx-sub">5つの研究所から、直近に公開した{new_count}件です。</p>
    </div>

    <ul class="idx-reports">
{new_articles}
    </ul>
  </div>
</section>

<section id="manifesto" class="idx-manifesto">
  <div class="wrap">
    <div class="idx-rule"></div>
    <h2>「答え」ではなく、「実験」を届ける。</h2>
    <p>人生ラボは、断言しません。キャリアも、育児も、お金の判断も、正解は人によって違うからです。私たちがやるのは、実際に試し、記録し、うまくいったこと・いかなかったことを研究所ごとに蓄積していくこと。</p>
    <p>それぞれの研究所は独立して育ちますが、根っこは1つ。「人生をより良くする」という問いに対して、AIと一緒に、地道に実験を重ねる場所であることです。その根っこにある考え方は、<a href="brand.html">7つの鍵</a>としてまとめています。運営しているのは、<a href="about.html">こんな人</a>です。</p>
  </div>
</section>
{ga_events}
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


def pick_related(article, lab, articles_by_lab, limit=4):
    """関連記事を「関連度」で選ぶ。

    従来は同じ研究所の最新3本を全記事に貼っていたため、キャリア28記事のうち
    25記事が同じ3本を指しており、内部リンクが数本の記事に集中していた。
    タグ・カテゴリの一致でスコアリングし、研究所をまたぐ関連も拾う。

    スコア: 共通タグ +3 / 同カテゴリ +4 / 同研究所 +1
    同点は新しい記事を優先。スコア0(接点なし)の記事は候補から外し、
    埋め合わせに同研究所の新しい記事を使う。
    """
    my_tags = set(article.get("tags") or [])
    my_cat = article.get("category")
    scored = []
    for other_lab, others in articles_by_lab.items():
        for o in others:
            if o["slug"] == article["slug"]:
                continue
            score = 3 * len(my_tags & set(o.get("tags") or []))
            if my_cat and o.get("category") == my_cat:
                score += 4
            if other_lab == lab:
                score += 1
            scored.append((score, str(o.get("date", "")), other_lab, o))

    scored.sort(key=lambda x: (-x[0], x[1] == "", x[1]), reverse=False)
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)

    picked = [(l, o) for s, _, l, o in scored if s > 0][:limit]

    if len(picked) < limit:  # 接点のある記事が足りなければ同研究所の新着で補う
        have = {o["slug"] for _, o in picked}
        for o in articles_by_lab.get(lab, []):
            if len(picked) >= limit:
                break
            if o["slug"] != article["slug"] and o["slug"] not in have:
                picked.append((lab, o))
                have.add(o["slug"])
    return picked


def build_article_pages(articles_by_lab):
    for lab, articles in articles_by_lab.items():
        info = LABS[lab]
        out_dir = os.path.join(LABS_DIR, lab)
        os.makedirs(out_dir, exist_ok=True)
        for i, a in enumerate(articles):
            related_html = "\n".join(
                RELATED_CARD.format(
                    href=(f'{o["slug"]}.html' if o_lab == lab else f'../{o_lab}/{o["slug"]}.html'),
                    accent=LABS[o_lab]["accent"],
                    # 他研究所の記事は、どこの記事か分かるよう研究所名を出す
                    cat_label=(o.get("category", "") if o_lab == lab
                               else f'{LABS[o_lab]["name"]} / {o.get("category", "")}'),
                    title=o["title"],
                )
                for o_lab, o in pick_related(a, lab, articles_by_lab)
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
                        banner=(
                            f'\n  <div class="cta-banner">\n{a["cta_banner_html"].strip()}\n  </div>'
                            if a.get("cta_banner_html") else ""
                        ),
                    ) if a.get("cta_url") else ""
                ),
                disclosure=(
                    FINANCIAL_RISK_DISCLOSURE_HTML if a.get("financial_risk")
                    else DISCLOSURE_HTML if a.get("affiliate") else ""
                ),
                related=related_html,
                code=info["code"],
                ga_events=GA_EVENTS_SNIPPET,
            )
            out_path = os.path.join(out_dir, f"{a['slug']}.html")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"generated article: labs/{lab}/{a['slug']}.html")


def apply_css_cache_busting():
    """style.cssのURLに内容ハッシュ(?v=xxxx)を付ける。

    Cloudflare Pagesは style.css を `max-age=14400`(4時間)で配信する一方、
    HTMLは `max-age=0` で毎回再検証される。この差があるため、ハッシュを
    付けないままCSSを更新すると「新しいHTML + 古いCSS」の組み合わせが
    最大4時間続き、訪問者にはレイアウトが崩れて見える(実際に発生した)。
    CSSの中身が変わったときだけURLが変わるので、更新時は確実に再取得され、
    変えていない間はキャッシュがそのまま効く。
    """
    css_path = os.path.join(ROOT, "style.css")
    if not os.path.exists(css_path):
        print("WARN: style.css が見つからないためキャッシュ対策を適用しません")
        return None
    with open(css_path, "rb") as f:
        digest = hashlib.md5(f.read()).hexdigest()[:8]

    targets = [
        "ARTICLE_TEMPLATE", "ABOUT_TEMPLATE", "LAB_INDEX_TEMPLATE",
        "BRAND_ARTICLE_TEMPLATE", "BRAND_INDEX_TEMPLATE", "INDEX_TEMPLATE",
    ]
    patched = 0
    for name in targets:
        tpl = globals()[name]
        if 'style.css?v=' in tpl:
            continue  # 二重適用を防ぐ
        new_tpl = tpl.replace('style.css"', f'style.css?v={digest}"')
        if new_tpl != tpl:
            globals()[name] = new_tpl
            patched += 1
    print(f"applied css cache-busting: style.css?v={digest} ({patched} templates)")
    return digest


def load_english_log():
    """data/english_log.yaml を読み込む。無ければ None(=英語専用ブロックを出さない)。"""
    path = os.path.join(ROOT, "data", "english_log.yaml")
    if not os.path.exists(path):
        print("INFO: data/english_log.yaml が無いため英語研究所の学習ログは生成しません")
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    data.setdefault("entries", [])
    if data["entries"] is None:
        data["entries"] = []
    return data


def build_english_blocks(log):
    """英語研究所の「現在地パネル」と「C1進捗＋語彙ログ」HTMLを組み立てる。
    件数・日数はすべて entries の実データから数える(推定値は出さない)。"""
    if log is None:
        return "", ""

    entries = list(log.get("entries") or [])
    for e in entries:
        e.setdefault("type", "word")
    entries.sort(key=lambda e: str(e.get("date", "")), reverse=True)

    words = sum(1 for e in entries if e.get("type") == "word")
    phrases = sum(1 for e in entries if e.get("type") == "phrase")
    hours = log.get("study_hours", 0) or 0
    days = len({str(e.get("date", "")) for e in entries if e.get("date")})

    level = log.get("level", {}) or {}
    targets = log.get("targets", {}) or {}
    t_words = targets.get("words", 3000)
    t_phrases = targets.get("phrases", 3000)
    h_min = targets.get("hours_min", 500)
    h_max = targets.get("hours_max", 800)

    panel = ELAB_PANEL.format(
        current=level.get("current", "B2"), target=level.get("target", "C1"),
        words=f"{words:,}", phrases=f"{phrases:,}", hours=f"{hours:,}", days=days,
    )

    def pct(done, goal):
        return 0 if not goal else min(100, round(done / goal * 100, 1))

    bars = "\n".join([
        ELAB_BAR.format(
            label="語彙", done=f"{words:,}", goal=f"{t_words:,}語",
            pct=pct(words, t_words),
            note=f"残り{max(0, t_words - words):,}語。",
        ),
        ELAB_BAR.format(
            label="フレーズ", done=f"{phrases:,}", goal=f"{t_phrases:,}件",
            pct=pct(phrases, t_phrases),
            note=f"残り{max(0, t_phrases - phrases):,}件。",
        ),
        ELAB_BAR.format(
            label="学習時間", done=f"{hours:,}", goal=f"{h_max:,}時間",
            pct=pct(hours, h_max),
            note=f"C1到達の目安は{h_min:,}〜{h_max:,}時間。バーは上限の{h_max:,}時間を100%として表示しています。",
        ),
    ])

    def _attr(v):
        return html_mod.escape(str(v), quote=True)

    if entries:
        items = "\n".join(
            ELAB_ENTRY.format(
                type=e.get("type", "word"),
                type_label="フレーズ" if e.get("type") == "phrase" else "単語",
                date=e.get("date", ""), term=e.get("term", ""),
                term_key=_attr(str(e.get("term", "")).lower()),
                # 検索対象: 単語・意味・例文・場面をまとめて小文字化しておく
                search_key=_attr(" ".join(str(e.get(k, "")) for k in
                                          ("term", "meaning", "example", "situation")).lower()),
                meaning=e.get("meaning", ""), example=e.get("example", ""),
                # 「使いたかった場面」は未記入なら枠ごと出さない(空のラベルを残さない)
                situation=(
                    ELAB_SITUATION.format(situation=e["situation"])
                    if e.get("situation") else ""
                ),
            )
            for e in entries
        )
        log_body = (f'    <ul class="elab-entries" id="elabEntries">\n{items}\n    </ul>\n'
                    '    <button type="button" class="elab-more" id="elabMore" hidden></button>')
        controls, script = ELAB_CONTROLS, ELAB_SCRIPT
    else:
        log_body = ELAB_EMPTY
        controls, script = "", ""

    feature = ELAB_FEATURE.format(bars=bars, log_body=log_body,
                                  controls=controls, script=script)
    return panel, feature


def build_lab_indexes(articles_by_lab, english_log=None):
    english_panel, english_feature = build_english_blocks(english_log)
    for lab, info in LABS.items():
        articles = articles_by_lab.get(lab, [])
        if articles:
            if lab == "career":
                hiring = [a for a in articles if a["slug"] in CAREER_HIRING_INTERVIEW_SLUGS]
                other = [a for a in articles if a["slug"] not in CAREER_HIRING_INTERVIEW_SLUGS]
                groups = []
                if hiring:
                    items = "\n".join(
                        CLAB_REPORT_ITEM.format(lab=lab, slug=a["slug"], date=a.get("date", ""), title=a["title"])
                        for a in hiring
                    )
                    groups.append(CLAB_REPORT_GROUP.format(group_name="採用・面接", items=items))
                if other:
                    items = "\n".join(
                        CLAB_REPORT_ITEM.format(lab=lab, slug=a["slug"], date=a.get("date", ""), title=a["title"])
                        for a in other
                    )
                    groups.append(CLAB_REPORT_GROUP.format(group_name="その他", items=items))
                article_section = '  <div class="clab-report-groups">\n' + "\n".join(groups) + "\n  </div>"
            else:
                cards = "\n".join(
                    ARTICLE_CARD.format(
                        lab=lab, slug=a["slug"], category=a.get("category", ""),
                        title=a["title"], description=a.get("description", "")
                    )
                    for a in articles
                )
                article_section = f'<div class="article-grid entry-{info["accent"]}">\n{cards}\n  </div>\n  '
            count_label = f"{len(articles)} ARTICLES"
        else:
            empty_note = '<p class="placeholder-note">この研究所は準備中です。記事は順次公開されます。</p>'
            article_section = f'<div class="article-grid entry-{info["accent"]}">\n\n  </div>\n  {empty_note}'
            count_label = "PREPARING"

        html = LAB_INDEX_TEMPLATE.format(
            name=info["name"], accent=info["accent"], code=info["code"],
            eyebrow=info["eyebrow"], lead=info["lead"],
            name_policy=info.get("name_policy", ""),
            diagnostic_cta=info.get("diagnostic_cta", ""),
            diag_flow_cta=info.get("diag_flow_cta", ""),
            note_series_cta=info.get("note_series_cta", ""),
            consult_cta=info.get("consult_cta", ""),
            director_cta=info.get("director_cta", ""),
            lab_panel=english_panel if lab == "english" else "",
            lab_feature=english_feature if lab == "english" else "",
            article_section=article_section, count_label=count_label,
            ga_events=GA_EVENTS_SNIPPET,
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


def build_index_page(articles_by_lab, english_log=None, n=8, per_lab=3):
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
            IDX_REPORT_ITEM.format(
                lab=lab, slug=a["slug"], lab_name=info["name"],
                title=a["title"], date=a.get("date", ""),
            )
            for _, lab, info, a in latest
        )
    else:
        cards = '      <li><p class="placeholder-note">まだ記事がありません。</p></li>'

    # 研究所ブロック: 各研究所の最新記事をトップページに直接出し、回遊の入口を増やす
    lab_blocks = []
    for lab, info in LABS.items():
        articles = articles_by_lab.get(lab, [])
        meta = INDEX_LAB_META[lab]
        if articles:
            items = "\n".join(
                IDX_LAB_ARTICLE.format(lab=lab, slug=a["slug"], title=a["title"])
                for a in articles[:per_lab]
            )
        else:
            items = '          <li><span class="idx-lab-empty">記事は準備中です</span></li>'
        lab_blocks.append(IDX_LAB_BLOCK.format(
            lab=lab, accent=info["accent"], code=info["code"], name=info["name"],
            desc=meta["desc"],
            tags="".join(f"<span>{t}</span>" for t in meta["tags"]),
            tool=meta["tool"], count=len(articles), articles=items,
        ))

    # FOLLOWカード: 英語ログに実データがあるときだけ出す(空のカードは出さない)
    follow_card = ""
    if english_log:
        ents = english_log.get("entries") or []
        if ents:
            days = len({str(e.get("date", "")) for e in ents if e.get("date")})
            follow_card = IDX_FOLLOW_CARD.format(days=days, items=f"{len(ents)}件")

    html = INDEX_TEMPLATE.format(
        new_articles=cards, new_count=len(latest),
        lab_blocks="\n".join(lab_blocks),
        follow_card=follow_card,
        ga_events=GA_EVENTS_SNIPPET,
    )
    out_path = os.path.join(ROOT, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    total_links = len(latest) + sum(min(len(v), per_lab) for v in articles_by_lab.values())
    print(f"updated: index.html (新着{len(latest)}件 + 研究所別{per_lab}件ずつ = 記事リンク{total_links}本)")


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


# build.pyが自動検出できない、手動管理の単体ページ一覧(specialpage_1のような
# 完全独立LPはここに含めない方針。含めるかは別途判断する)
STANDALONE_PAGES = [
    "labs/career-diagnosis",
]


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

    # 手動管理の単体ページを別系統で追記(上記の自動検出ロジックには一切触れない)
    for path in STANDALONE_PAGES:
        urls.append(f"{base_url}/{path}")

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
    apply_css_cache_busting()
    articles_by_lab = load_articles()
    brand_articles = load_brand_articles()
    english_log = load_english_log()
    build_article_pages(articles_by_lab)
    build_lab_indexes(articles_by_lab, english_log)
    build_brand_pages(brand_articles)
    build_brand_index(brand_articles)
    build_about_page()
    build_index_page(articles_by_lab, english_log)
    build_sns_drafts(articles_by_lab)
    build_sitemap(articles_by_lab, brand_articles)
    total = sum(len(v) for v in articles_by_lab.values())
    print(f"\nDone. {total} lab articles + {len(brand_articles)} brand articles processed.")
