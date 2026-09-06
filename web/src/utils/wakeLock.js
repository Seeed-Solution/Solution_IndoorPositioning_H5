// 展示模式的防熄屏（spec §9.5）。
//
// `navigator.wakeLock` 只在安全上下文 + 支持的浏览器里有；拿不到就静默降级，
// 展示模式本身不能因此不可用。系统会在页面切到后台时主动释放 sentinel，
// 所以回到前台必须重新申请，否则第一次切标签页之后屏幕就又会睡。

export function createWakeLock({
  nav = typeof navigator !== 'undefined' ? navigator : null,
  doc = typeof document !== 'undefined' ? document : null,
} = {}) {
  let sentinel = null;
  let wanted = false;

  const supported = () => typeof nav?.wakeLock?.request === 'function';

  const acquire = async () => {
    if (!wanted || !supported() || sentinel) return false;
    try {
      sentinel = await nav.wakeLock.request('screen');
      sentinel.addEventListener?.('release', () => { sentinel = null; });
      return true;
    } catch (err) {
      // 失败静默: 未授权、非安全上下文、省电模式都会走这里
      sentinel = null;
      return false;
    }
  };

  const drop = async () => {
    const held = sentinel;
    sentinel = null;
    if (!held) return;
    try {
      await held.release?.();
    } catch (err) {
      /* 释放失败无所谓: 页面走了系统自己会收 */
    }
  };

  const onVisibilityChange = () => {
    if (!wanted) return;
    if (doc?.visibilityState === 'visible') acquire();
  };

  return {
    /** 申请并挂上回前台重申请的监听。 */
    start() {
      if (wanted) return;
      wanted = true;
      doc?.addEventListener?.('visibilitychange', onVisibilityChange);
      acquire();
    },
    /** 离开展示模式/卸载时释放。 */
    stop() {
      if (!wanted) return;
      wanted = false;
      doc?.removeEventListener?.('visibilitychange', onVisibilityChange);
      drop();
    },
    get supported() {
      return supported();
    },
    get held() {
      return sentinel !== null;
    },
  };
}
