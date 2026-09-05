/* quiz.js — correction immédiate avec feedback par option, progression, score commenté,
   mémorisation locale, résultats par étape sur la page finale. */
const $ = (s, c = document) => c.querySelector(s);
const $$ = (s, c = document) => Array.from(c.querySelectorAll(s));
const store = {
  get(k, d = null) { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* ignore */ } },
};
$$('[data-quiz]').forEach(initQuiz);

function initQuiz(section) {
  const key = 'quiz:' + section.dataset.quiz;
  const cards = $$('.qz', section);
  const score = $('.score', section);
  const reset = $('[data-quiz-reset]', section);
  const prog = $('.qprog', section);
  let state = store.get(key, { answers: {} });
  if (!state || typeof state.answers !== 'object') state = { answers: {} };
  const total = cards.length;

  function paint(justAnswered) {
    cards.forEach((c) => {
      const qi = c.dataset.q;
      const a = Number(c.dataset.a);
      const buttons = $$('button', c);
      const fb = $('.fb', c);
      const chosen = state.answers[qi];
      buttons.forEach((b, k) => {
        b.disabled = chosen !== undefined;
        b.classList.remove('ok', 'ko', 'shown');
        b.setAttribute('aria-pressed', String(chosen === k));
      });
      fb.classList.remove('show', 'good', 'bad');
      const v = $('.v', fb);
      if (v) v.remove();
      if (chosen !== undefined) {
        buttons[a].classList.add('ok', 'shown');
        if (chosen !== a) buttons[chosen].classList.add('ko', 'shown');
        fb.classList.add('show', chosen === a ? 'good' : 'bad');
        const b = document.createElement('b');
        b.className = 'v';
        b.textContent = chosen === a ? 'Exact.' : 'Pas tout à fait.';
        fb.prepend(b);
      }
    });
    const answered = Object.keys(state.answers).length;
    const correct = cards.filter((c) => state.answers[c.dataset.q] === Number(c.dataset.a)).length;
    if (prog) {
      prog.hidden = answered === 0;
      prog.textContent = answered < total
        ? `${answered} question${answered > 1 ? 's' : ''} sur ${total} · ${correct} juste${correct > 1 ? 's' : ''}`
        : `Terminé : ${correct} sur ${total}`;
    }
    if (answered === total && total) {
      const rate = correct / total;
      const misses = cards.filter((c) => state.answers[c.dataset.q] !== Number(c.dataset.a));
      const links = misses.map((c) => {
        const sec = $('.qsec', c);
        return sec ? `<a href="${sec.getAttribute('href')}">question ${Number(c.dataset.q) + 1}</a>` : `question ${Number(c.dataset.q) + 1}`;
      });
      let msg;
      if (rate === 1) msg = 'Tout est juste. Vous pouvez passer à la suite.';
      else if (rate >= 0.7) msg = 'Les repères sont là. Relisez les passages liés aux questions manquées : ';
      else msg = 'Reprenez la lecture du module, puis refaites le quiz. À revoir : ';
      score.innerHTML = `<strong>Score : ${correct} sur ${total}.</strong> ${msg}${rate < 1 ? links.join(', ') + '.' : ''}`;
      score.classList.add('show');
      reset.hidden = false;
      if (justAnswered) score.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    } else {
      score.classList.remove('show');
      reset.hidden = answered === 0;
    }
    store.set(key, { answers: state.answers, correct, total, at: Date.now() });
  }

  cards.forEach((c) => {
    $$('button', c).forEach((b) => b.addEventListener('click', () => {
      if (state.answers[c.dataset.q] !== undefined) return;
      state.answers[c.dataset.q] = Number(b.dataset.i);
      const wasLast = Object.keys(state.answers).length === total;
      paint(wasLast);
      if (!wasLast) {
        const fb = $('.fb', c);
        fb && fb.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      }
    }));
  });
  reset.addEventListener('click', () => {
    state = { answers: {} };
    paint(false);
    cards[0].scrollIntoView({ block: 'start', behavior: 'smooth' });
    $('button', cards[0]).focus({ preventScroll: true });
  });
  paint(false);
}

/* résultats par étape (page Consolider) */
const stepsBox = $('[data-quiz-steps]');
if (stepsBox) {
  const steps = JSON.parse(stepsBox.dataset.quizSteps || '[]');
  const rows = steps.map((st) => {
    let c = 0;
    let t = 0;
    st.modules.forEach((m) => { const s = store.get('quiz:' + m); if (s && s.total) { c += s.correct || 0; t += s.total; } });
    return { key: st.key, title: st.title, c, t };
  });
  const any = rows.some((r) => r.t);
  stepsBox.innerHTML = any
    ? '<div class="tw tw--narrow"><table><thead><tr><th>Étape</th><th>Quiz des modules</th></tr></thead><tbody>'
      + rows.map((r) => `<tr><td>${r.key} · ${r.title}</td><td>${r.t ? `${r.c} / ${r.t} bonnes réponses` : 'non encore fait'}</td></tr>`).join('')
      + '</tbody></table></div>'
    : '<p class="muted">Vous n\'avez pas encore répondu aux quiz des modules sur cet appareil.</p>';
  const radar = $('[data-radar]');
  if (radar && any) radar.dispatchEvent(new CustomEvent('pea:radar', { detail: rows }));
}
