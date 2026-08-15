/* ==========================================================================
   見えない評価ギャップ診断 — ロジック
   仕様: docs/career-diagnostic-spec.md
   サーバー不要。スコアリングはブラウザ内のみで完結。
   メール登録のみ、既存のGoogleフォームにno-corsで裏側送信する。
   ========================================================================== */

(function () {
  "use strict";

  // 詳細版メール登録フォーム(運営者提供の実URL・entry ID)
  var FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSfXWQn2Jzgn-2nM_1HwDe3G77aKylT2_YdMZ1s7CRqseNiwBw/formResponse";
  var ENTRY_EMAIL = "entry.2113694273";
  var ENTRY_TYPE = "entry.1853879079";

  var THREADS_URL = "https://www.threads.net/@mylifejinseilab";

  // ---- 5軸の定義(仕様書 §1) ----
  var AXES = {
    A: { name: "可視化ギャップ", max: 9 },
    B: { name: "推薦者ギャップ", max: 9 },
    C: { name: "評判伝播ギャップ", max: 6 },
    D: { name: "再現性ギャップ", max: 6 },
    E: { name: "タイミング・枠ギャップ", max: 6 },
  };
  var AXIS_ORDER = ["A", "B", "C", "D", "E"];

  // ---- 12問(仕様書 §2、文言そのまま) ----
  var QUESTIONS = [
    { axis: "A", text: "直近半年でいちばん誇れる成果を、あなた以外で最初に知ったのは誰ですか？", choices: [
      { label: "部門長・経営層など、評価を決める立場の人（自分から直接伝えた）", score: 0 },
      { label: "直属の上司。その後、上まで報告されたことも確認できている", score: 1 },
      { label: "直属の上司。ただし、その先どこまで伝わったかは分からない", score: 2 },
      { label: "同僚・チームメンバーまで。上には特に報告していない", score: 3 },
    ]},
    { axis: "A", text: "自分の成果は「誰の成果」として社内で語られていますか？", choices: [
      { label: "自分の名前で語られている確信がある。根拠もある", score: 0 },
      { label: "たぶん自分の成果として伝わっていると思う", score: 1 },
      { label: "チームの成果として語られている可能性がある", score: 2 },
      { label: "考えたことがない", score: 3 },
    ]},
    { axis: "A", text: "自分の評価に直接関わる人（直属の上司のさらに上）と、直接話す機会は？", choices: [
      { label: "月1回以上、業務の話で直接接点がある", score: 0 },
      { label: "数ヶ月に1回程度ある", score: 1 },
      { label: "評価面談以外ではほぼ接点がない", score: 2 },
      { label: "一度も直接話したことがない", score: 3 },
    ]},
    { axis: "B", text: "自分が今狙っているポジションについて、自分以外に言ってくれる人は？", choices: [
      { label: "複数人思い浮かぶ。実際に言ってくれた実績もある", score: 0 },
      { label: "1人は思い浮かぶ", score: 1 },
      { label: "頼んだことはあるが、実際に言ってくれたかは分からない", score: 2 },
      { label: "誰にも頼んだことがない。実力で見てもらえると思っている", score: 3 },
    ]},
    { axis: "B", text: "自分が急に1ヶ月休んだら、いちばん困るのは誰ですか？", choices: [
      { label: "他部門や経営層。実際に「あなたがいないと困る」と言われたことがある", score: 0 },
      { label: "直属の上司。すぐに気づいて困るはず", score: 1 },
      { label: "自分のチーム内。外から見れば大きな影響はない", score: 2 },
      { label: "特に誰も困らない。すぐに代わりが立つと思う", score: 3 },
    ]},
    { axis: "B", text: "昇格や異動を検討する会議に、自分について「補足」してくれそうな人は？", choices: [
      { label: "具体的に思い浮かぶ。直近で実際に助けてもらった実感がある", score: 0 },
      { label: "おそらく上司はフォローしてくれると思う", score: 1 },
      { label: "誰がその会議に出ているかも把握していない", score: 2 },
      { label: "そういう会議があること自体、意識したことがない", score: 3 },
    ]},
    { axis: "C", text: "他部署の人から「一緒に仕事をしたい」と名前を挙げてもらえるとしたら、何人くらいだと思いますか？", choices: [
      { label: "5人以上。実際に言われたことがある", score: 0 },
      { label: "2〜3人は思い浮かぶ", score: 1 },
      { label: "1人いるかどうか", score: 2 },
      { label: "分からない。他部署との接点がほとんどない", score: 3 },
    ]},
    { axis: "C", text: "直近1年で、他部署や斜め上のマネージャーから直接フィードバックをもらったことは？", choices: [
      { label: "ある。褒められたことも指摘されたこともある", score: 0 },
      { label: "褒められたことはある", score: 1 },
      { label: "ほぼない", score: 2 },
      { label: "一度もない", score: 3 },
    ]},
    { axis: "D", text: "「今の役割は申し分ないが、一つ上は未知数」と見られている可能性について、何かしていますか？", choices: [
      { label: "懸念を払拭する行動を意識的に取っている（例：一つ上の業務を一部担当している）", score: 0 },
      { label: "特に対策はしていないが、任せてもらえればできると思う", score: 1 },
      { label: "今の役割で手一杯で、次のことは考えられていない", score: 2 },
      { label: "考えたことがない", score: 3 },
    ]},
    { axis: "D", text: "直近で「これは一つ上のレベルの仕事だった」と、具体的に説明できる経験は？", choices: [
      { label: "複数ある。状況・判断・結果まで説明できる", score: 0 },
      { label: "1つならある", score: 1 },
      { label: "あるかもしれないが、うまく説明できない", score: 2 },
      { label: "ない。与えられた範囲の仕事しかしていない", score: 3 },
    ]},
    { axis: "E", text: "自分の評価・昇格が「実力」以外の要因（昇格枠、上司の在任期間、事業状況）で左右される可能性を、どう捉えていますか？", choices: [
      { label: "自社の昇格サイクルや枠の状況を具体的に把握している", score: 0 },
      { label: "何となく影響はあるだろうと思っている", score: 1 },
      { label: "考えたことがない。実力で決まると思っている", score: 2 },
      { label: "実力がすべてだと強く信じている。枠の話は言い訳だと思う", score: 3 },
    ]},
    { axis: "E", text: "評価・昇格が見送られたとき、最初に疑うのは？", choices: [
      { label: "実力・可視化・タイミングなど複数の要因を切り分けて考える", score: 0 },
      { label: "まず自分の実力不足を疑う", score: 1 },
      { label: "まず上司との相性やタイミングを疑う", score: 2 },
      { label: "分からない。理由を深く聞いたことがない", score: 3 },
    ]},
  ];

  // ---- 結果文言(仕様書 §4、文言そのまま) ----
  var RESULT_CONTENT = {
    A: {
      title: "診断結果：可視化ギャップ",
      body: [
        "あなたの成果は、おそらく直属の上司より先に届いていません。",
        "昇格や評価の会議に出ているのは、あなたではなく上司です。そこで語られる「あなたの成果」は、上司の記憶と伝え方に依存しています。どれだけ良い仕事をしても、それがテーブルに乗る形で伝わっていなければ、無かったことと同じ扱いを受けます。",
        "これは能力の問題ではなく、情報の設計の問題です。",
      ],
    },
    B: {
      title: "診断結果：推薦者ギャップ",
      body: [
        "昇格や異動は、あなたがいない部屋で決まります。",
        "その部屋で誰もあなたの名前を挙げなければ、どれだけ実力があっても検討の対象にすら乗りません。「実力で見てもらえる」という前提は、その部屋に自分の代わりに話す人がいて初めて成り立ちます。",
        "今のあなたには、その部屋で話す人が足りていない可能性があります。",
      ],
    },
    C: {
      title: "診断結果：評判伝播ギャップ",
      body: [
        "あなたの評判は、あなたの知らない経路を通っています。",
        "意思決定者は、直属の上司の評価だけで判断しません。他部署からの評判、斜め上のマネージャーの一言、そうした間接的な情報を無意識に参照します。この経路に何も流れていなければ、いくら直属の上司の評価が高くても、\"よく知らない人\"という扱いのまま止まります。",
      ],
    },
    D: {
      title: "診断結果：再現性ギャップ",
      body: [
        "今の役割が完璧なことと、次の役割で困らないことは、別の審査です。",
        "人事や上司が最後に迷うのは、能力ではなく再現性です。「一つ上のレベルでも同じようにやれる」という具体的な証拠がなければ、実績があるほど「今のポジションの方が向いている」という結論に落ち着きやすくなります。",
      ],
    },
    E: {
      title: "診断結果：タイミング・枠ギャップ",
      body: [
        "評価や昇格の見送りを、すべて自分の実力の問題として処理していませんか。",
        "実際には、昇格枠の数、上司の在任期間、事業のフェーズといった、本人の実力と無関係な要因が結果を左右することがあります。この要因を一切考慮しないと、直すべきでない部分まで直そうとして消耗します。逆に、この要因だけに逃げ込むのも危険です。",
      ],
    },
  };

  var COMMON_FOOTER = "この診断が示せるのは、12の質問から見える傾向までです。実際の状況は、業界・役職・組織のフェーズによって大きく変わります。";

  // ---- ブロック3: 関連研究(タイプ別リンク。運営者確定分のみ。creative fabricationはしない) ----
  var RELATED_LINKS = {
    A: { title: "在宅勤務で評価されにくいと感じたときの対策", url: "/labs/career/remote-work-evaluation-concerns", external: false },
    B: { title: "あなたの上司は、あなたを「推せない」かもしれない", url: "https://note.com/key7life/n/n877672332f17", external: true },
    C: { title: "あなたの評価は見知らぬ後輩が作る", url: "https://note.com/key7life/n/n4effa72505ff", external: true },
    D: { title: "「左遷」と言われる場所が、実はチャンスである理由", url: "https://note.com/key7life/n/n22a9aa90e349", external: true },
    E: { title: "評価は高いのに昇格しない。その理由は「隣の課長」にあります", url: "https://note.com/key7life/n/ndb619c156417", external: true },
  };

  // ---- 状態 ----
  var state = {
    answers: new Array(QUESTIONS.length).fill(null),
    currentIndex: 0,
  };

  var quizCard = document.getElementById("quizCard");
  var resultCard = document.getElementById("resultCard");
  var progressBar = document.getElementById("progressBar");
  var progressLabel = document.getElementById("progressLabel");
  var eyebrow = document.getElementById("diagEyebrow");

  function renderQuestion(index) {
    var q = QUESTIONS[index];
    var pct = Math.round((index / QUESTIONS.length) * 100);
    progressBar.style.width = pct + "%";
    progressLabel.textContent = "Q" + (index + 1) + " / " + QUESTIONS.length;

    var html = "";
    html += '<p class="diag-q-axis">' + AXES[q.axis].name + "</p>";
    html += '<p class="diag-q-text">' + escapeHtml(q.text) + "</p>";
    html += '<ul class="diag-choices">';
    q.choices.forEach(function (choice, ci) {
      var selected = state.answers[index] === ci ? " is-selected" : "";
      html +=
        '<li><button type="button" class="diag-choice' +
        selected +
        '" data-choice="' +
        ci +
        '">' +
        escapeHtml(choice.label) +
        "</button></li>";
    });
    html += "</ul>";
    if (index > 0) {
      html += '<a href="#" class="diag-back" id="diagBack">← 前の質問に戻る</a>';
    }
    quizCard.innerHTML = html;

    Array.prototype.forEach.call(quizCard.querySelectorAll(".diag-choice"), function (btn) {
      btn.addEventListener("click", function () {
        var ci = parseInt(btn.getAttribute("data-choice"), 10);
        selectChoice(index, ci);
      });
    });

    var backLink = document.getElementById("diagBack");
    if (backLink) {
      backLink.addEventListener("click", function (e) {
        e.preventDefault();
        state.currentIndex = index - 1;
        renderQuestion(state.currentIndex);
      });
    }
  }

  function selectChoice(index, choiceIndex) {
    if (index === 0 && state.answers[0] === null && typeof gtag === "function") {
      gtag("event", "diagnosis_start");  // 1問目に答えた時点を開始とみなす
    }
    state.answers[index] = choiceIndex;
    if (index < QUESTIONS.length - 1) {
      state.currentIndex = index + 1;
      renderQuestion(state.currentIndex);
    } else {
      progressBar.style.width = "100%";
      progressLabel.textContent = "診断完了";
      showResult();
    }
  }

  function computeScores() {
    var totals = { A: 0, B: 0, C: 0, D: 0, E: 0 };
    QUESTIONS.forEach(function (q, i) {
      var ci = state.answers[i];
      var score = ci === null ? 0 : q.choices[ci].score;
      totals[q.axis] += score;
    });
    var rates = {};
    AXIS_ORDER.forEach(function (axis) {
      rates[axis] = (totals[axis] / AXES[axis].max) * 100;
    });
    // 主たるギャップ: 得点率最大。同率はA→B→C→D→Eの順で優先
    var ranked = AXIS_ORDER.slice().sort(function (a, b) {
      if (rates[b] !== rates[a]) return rates[b] - rates[a];
      return AXIS_ORDER.indexOf(a) - AXIS_ORDER.indexOf(b);
    });
    var primary = ranked[0];
    var secondary = ranked[1];
    var isComposite = rates[primary] - rates[secondary] <= 10;
    return { totals: totals, rates: rates, primary: primary, secondary: secondary, isComposite: isComposite };
  }

  function showResult() {
    var scores = computeScores();
    var result = RESULT_CONTENT[scores.primary];

    eyebrow.textContent = "診断結果";
    eyebrow.classList.add("is-result");

    var html = "";
    html += '<p class="diag-result-type">' + AXES[scores.primary].name + "</p>";
    html += '<h2 class="diag-result-title">' + escapeHtml(result.title.replace("診断結果：", "")) + "</h2>";
    html += '<div class="diag-result-body">';
    result.body.forEach(function (p) {
      html += "<p>" + escapeHtml(p) + "</p>";
    });
    html += "</div>";

    if (scores.isComposite) {
      html +=
        '<p class="diag-result-composite">あなたにはもう一つ、〈' +
        AXES[scores.secondary].name +
        "〉の傾向も見られます。多くの場合、この2つは同時に起きます。</p>";
    }

    html += '<p class="diag-result-footer">' + escapeHtml(COMMON_FOOTER) + "</p>";

    // ブロック1: 詳細版(メール登録)
    html += '<div class="diag-cta-blocks">';
    html += '<div class="diag-cta-block">';
    html += "<h3>〈" + AXES[scores.primary].name + "〉を、どう埋めるか</h3>";
    html +=
      "<p>診断で分かるのはズレの場所までです。埋め方は状況によって変わります。詳細版では、このギャップが実際の評価・昇格の場でどう表れるか、どこから手をつけるべきかをまとめて送ります。</p>";
    html += '<form class="diag-email-form" id="emailForm">';
    html +=
      '<input type="email" class="diag-email-input" id="emailInput" placeholder="メールアドレス" required>';
    html += '<button type="submit" class="diag-btn" id="emailSubmit">詳細版を受け取る</button>';
    html += "</form>";
    html += '<p class="diag-email-status" id="emailStatus"></p>';
    html += "</div>";

    // ブロック2: 個別相談(DM)
    html += '<div class="diag-cta-block">';
    html += "<h3>12問では出ない部分</h3>";
    html +=
      "<p>業界・役職・社内の力学まで踏まえた話は、この診断ではできません。詳しい状況を聞いた上での相談は、Threadsで受けています。</p>";
    html +=
      '<a class="diag-btn diag-btn-outline" href="' +
      THREADS_URL +
      '" target="_blank" rel="noopener">DMで相談する</a>';
    html += "</div>";

    // ブロック3: 関連研究
    html += '<div class="diag-cta-block">';
    html += "<h3>関連レポート</h3>";
    var related = RELATED_LINKS[scores.primary];
    if (related) {
      html +=
        '<a class="diag-btn diag-btn-outline" href="' +
        related.url +
        '"' +
        (related.external ? ' target="_blank" rel="noopener"' : "") +
        ">" +
        escapeHtml(related.title) +
        "</a>";
    } else {
      html += "<p>関連レポート：準備中</p>";
    }
    html += "</div>";

    html += "</div>";

    resultCard.innerHTML = html;
    quizCard.hidden = true;
    resultCard.hidden = false;

    // 12問を最後まで進めた人の数と、出た型をGA4に送る
    if (typeof gtag === "function") {
      gtag("event", "diagnosis_complete", {
        result_type: scores.primary,
        is_composite: scores.isComposite,
      });
    }

    var form = document.getElementById("emailForm");
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      submitEmail(document.getElementById("emailInput").value, scores.primary);
    });
  }

  function submitEmail(email, typeAxis) {
    var statusEl = document.getElementById("emailStatus");
    var submitBtn = document.getElementById("emailSubmit");
    submitBtn.disabled = true;
    statusEl.textContent = "送信中…";
    statusEl.className = "diag-email-status";

    var body = new URLSearchParams();
    body.append(ENTRY_EMAIL, email);
    body.append(ENTRY_TYPE, typeAxis);

    fetch(FORM_URL, {
      method: "POST",
      mode: "no-cors",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: body.toString(),
    })
      .then(function () {
        // no-corsのためレスポンス内容は読めない。例外が出なければ送信成功とみなす。
        if (typeof gtag === "function") {
          gtag("event", "diagnosis_email_submit", { result_type: typeAxis });
        }
        statusEl.textContent = "登録しました。詳細版を送ります。";
        statusEl.className = "diag-email-status ok";
        submitBtn.textContent = "登録済み";
      })
      .catch(function () {
        statusEl.textContent = "送信に失敗しました。時間をおいて再度お試しください。";
        statusEl.className = "diag-email-status err";
        submitBtn.disabled = false;
      });
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  renderQuestion(0);
})();
