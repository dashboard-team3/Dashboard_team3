"""페이지 설정 · 기본 스타일 · 밝은 테마 (원본 app2.py 의 1. 공통 설정).

setup()      맨 먼저 부른다. 페이지 설정 → 어두운 CSS → 밝은 테마 CSS. 밝은 테마인지(True/False)를 돌려준다
theme_sync() 맨 끝에 부른다. 테마를 바꾸면 그래프 색까지 다시 그리게 하는 숨은 버튼 + 감시 스크립트
"""
import time

import streamlit as st

from core.paths import STYLE_DIR



# 밝은 테마: Streamlit 자체 설정(오른쪽 위 ⋮ → Settings → Theme)을 따른다. 밝은 테마면 밝은 CSS를 덧입히고 그래프 색도 맞춘다.
def _is_light():
    try:
        return st.context.theme.type == "light"
    except Exception:          # 오래된 Streamlit 에는 st.context.theme 이 없다
        return False




def _scope_css(css, prefix):
    """CSS 규칙마다 선택자 앞에 prefix 를 붙인다 (밝은 테마 CSS를 html[data-theme="light"] 아래로 가둔다)."""
    import re
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out = []
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        sels = [x.strip() for x in m.group(1).split(",") if x.strip()]
        sels = [prefix if x == "html" else f"{prefix} {x}" for x in sels]
        out.append(", ".join(sels) + " {" + m.group(2) + "}")
    return "\n".join(out)


# 테마가 바뀌면 Streamlit 은 앱을 다시 돌리지 않는다. 그래프 색까지 맞추려면 한 번 다시 그려야 하므로,
# 화면의 테마와 파이썬이 그린 테마가 다르면 숨은 버튼을 눌러 다시 실행한다 (세션 상태는 유지).
THEME_SCRIPT = """
(() => {
  const d = document, w = window, py = "__PY__";
  const sync = () => {
    const app = d.querySelector('.stApp'); if (!app) return;
    const cur = getComputedStyle(app).colorScheme === 'light' ? 'light' : 'dark';
    if (d.documentElement.dataset.theme !== cur) d.documentElement.dataset.theme = cur;
    if (cur !== py && !w.__themeSyncing) {
      w.__themeSyncing = true;
      const b = d.querySelector('.st-key-theme_sync button');
      if (b) b.click();
      setTimeout(() => { w.__themeSyncing = false; }, 4000);
    }
  };
  sync();
  // 마우스 말풍선(.tip): 화면 오른쪽 절반에 있는 글자는 말풍선을 왼쪽으로 펼쳐 화면 밖으로 잘리지 않게
  if (!w.__tipFlip) {
    w.__tipFlip = true;
    d.addEventListener('mouseover', (e) => {
      const t = e.target && e.target.closest ? e.target.closest('.tip') : null;
      if (!t) return;
      t.classList.toggle('r', t.getBoundingClientRect().left > w.innerWidth * 0.55);
    }, true);
  }
  if (w.__themeTimer) clearInterval(w.__themeTimer);
  w.__themeTimer = setInterval(sync, 600);
  // 웹 글꼴(Pretendard)이 늦게 오면 Plotly가 대체 글꼴 폭으로 여백을 재서 축 제목이 눈금과 겹친다 → 글꼴이 오면 한 번 다시 그린다
  if (d.fonts && !w.__fontRedraw) {
    w.__fontRedraw = true;
    d.fonts.ready.then(() => setTimeout(() => w.dispatchEvent(new Event('resize')), 150));
  }
})();
"""


def setup():
    st.set_page_config(page_title="Conflict Risk & Arms Dashboard", layout="wide")
    st.markdown(f"<style>{(STYLE_DIR / 'style2.css').read_text(encoding='utf-8')}</style>",
                unsafe_allow_html=True)   # styles/style2.css = 기본(어두운) 화면 스타일 전체
    light = _is_light()
    st.session_state["_light"] = light      # 모든 그래프가 이 테마를 따르게 (core/theme.py)
    # 밝은 테마 CSS는 늘 넣어 두되 html[data-theme="light"] 일 때만 살아난다. 이 속성은 THEME_SCRIPT 가
    # Streamlit 이 실제로 적용한 테마(.stApp 의 color-scheme)를 읽어 붙인다 → 테마를 바꾸는 즉시 화면이 따라간다.
    st.markdown("<style>" + _scope_css((STYLE_DIR / 'style_light.css').read_text(encoding='utf-8'), 'html[data-theme="light"]')
                + "\n.st-key-theme_sync { display: none; }</style>", unsafe_allow_html=True)
    return light


def theme_sync(light):
    """테마 동기화: 숨은 버튼 + 감시 스크립트 (위 THEME_SCRIPT 설명 참고). 페이지를 다 그린 뒤 부른다."""
    st.button("테마 동기화", key="theme_sync")
    st.html(f"<script>/* {time.time()} */{THEME_SCRIPT.replace('__PY__', 'light' if light else 'dark')}</script>",
            unsafe_allow_javascript=True)
