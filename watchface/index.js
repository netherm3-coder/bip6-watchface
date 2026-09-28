// Циферблат «Orange Time» для Amazfit Bip 6 (Zepp OS 5, екран 390x450).
// Великий час, під ним «28 ВЕР», ще нижче «ПН». Однаково на активному екрані й в AOD.
//
// Час, дату й день тижня малюють системні віджети IMG_TIME / IMG_DATE / IMG_WEEK:
// їх оновлює прошивка, тож вони працюють і при вимкненому екрані (AOD), коли JS може стояти.
// Якщо якогось із них немає в прошивці, той самий елемент малюється звичайними картинками
// й оновлюється щохвилини з JS, щоб циферблат не лишився чорним.

import * as hmUI from '@zos/ui'
import { px } from '@zos/utils'
import { Time } from '@zos/sensor'

// Координати генерує tools/gen_assets.py — не правте вручну.
// <layout>
const COLON_X = 178
const DATE_DIGIT_W = 27
const DATE_Y = 296
const DAY_X = 121
const DIGIT_W = 80
const HOUR_X = 18
const MINUTE_X = 212
const MONTH_X = 189
const TIME_Y = 62
const WEEK_X = 166
const WEEK_Y = 349
// </layout>

const range = (n, from = 0) => Array.from({ length: n }, (_, i) => i + from)
const TIME_DIGITS = range(10).map((i) => `time/${i}.png`)
const DATE_DIGITS = range(10).map((i) => `date/${i}.png`)
const MONTHS = range(12, 1).map((i) => `month/${i}.png`)
const WEEKDAYS = range(7, 1).map((i) => `week/${i}.png`) // 1 = понеділок

const W = hmUI.widget
const BOTH = hmUI.show_level.ONLY_NORMAL | hmUI.show_level.ONAL_AOD

function create(type, options) {
  return hmUI.createWidget(type, Object.assign({ show_level: BOTH }, options))
}

// Повертає true, якщо системний віджет створено.
function tryNative(name, build) {
  if (W[name] === undefined || W[name] === null) return false
  try {
    build()
    return true
  } catch (e) {
    console.log(`Orange Time: ${name} failed: ${e}`)
    return false
  }
}

function nativeTime() {
  create(W.IMG_TIME, {
    hour_zero: 1,
    hour_startX: px(HOUR_X),
    hour_startY: px(TIME_Y),
    hour_array: TIME_DIGITS,
    hour_space: 0,
    hour_align: hmUI.align.LEFT,
    minute_zero: 1,
    minute_startX: px(MINUTE_X),
    minute_startY: px(TIME_Y),
    minute_array: TIME_DIGITS,
    minute_space: 0,
    minute_follow: 0,
    minute_align: hmUI.align.LEFT,
  })
}

function nativeDate() {
  create(W.IMG_DATE, {
    day_startX: px(DAY_X),
    day_startY: px(DATE_Y),
    day_zero: 1,
    day_space: 0,
    day_follow: 0,
    day_align: hmUI.align.LEFT,
    day_en_array: DATE_DIGITS,
    day_sc_array: DATE_DIGITS,
    day_tc_array: DATE_DIGITS,
    month_startX: px(MONTH_X),
    month_startY: px(DATE_Y),
    month_is_character: true,
    month_space: 0,
    month_follow: 0,
    month_align: hmUI.align.LEFT,
    month_en_array: MONTHS,
    month_sc_array: MONTHS,
    month_tc_array: MONTHS,
  })
}

function nativeWeek() {
  create(W.IMG_WEEK, {
    x: px(WEEK_X),
    y: px(WEEK_Y),
    week_en: WEEKDAYS,
    week_tc: WEEKDAYS,
    week_sc: WEEKDAYS,
  })
}

// Запасний варіант: окремі картинки, оновлення щохвилини з JS.
function fallback(need) {
  const time = new Time()
  // стартова картинка того ж розміру, що й наступні: віджет бере розмір із неї
  const img = (x, y, src) => create(W.IMG, { x: px(x), y: px(y), src })
  const cells = []

  if (need.time) {
    const h1 = img(HOUR_X, TIME_Y, TIME_DIGITS[0])
    const h2 = img(HOUR_X + DIGIT_W, TIME_Y, TIME_DIGITS[0])
    const m1 = img(MINUTE_X, TIME_Y, TIME_DIGITS[0])
    const m2 = img(MINUTE_X + DIGIT_W, TIME_Y, TIME_DIGITS[0])
    cells.push(() => {
      const h = time.getHours()
      const m = time.getMinutes()
      h1.setProperty(hmUI.prop.SRC, TIME_DIGITS[Math.floor(h / 10)])
      h2.setProperty(hmUI.prop.SRC, TIME_DIGITS[h % 10])
      m1.setProperty(hmUI.prop.SRC, TIME_DIGITS[Math.floor(m / 10)])
      m2.setProperty(hmUI.prop.SRC, TIME_DIGITS[m % 10])
    })
  }
  if (need.date) {
    const d1 = img(DAY_X, DATE_Y, DATE_DIGITS[0])
    const d2 = img(DAY_X + DATE_DIGIT_W, DATE_Y, DATE_DIGITS[0])
    const mon = img(MONTH_X, DATE_Y, MONTHS[0])
    cells.push(() => {
      const d = time.getDate()
      d1.setProperty(hmUI.prop.SRC, DATE_DIGITS[Math.floor(d / 10)])
      d2.setProperty(hmUI.prop.SRC, DATE_DIGITS[d % 10])
      mon.setProperty(hmUI.prop.SRC, MONTHS[time.getMonth() - 1])
    })
  }
  if (need.week) {
    const wk = img(WEEK_X, WEEK_Y, WEEKDAYS[0])
    cells.push(() => wk.setProperty(hmUI.prop.SRC, WEEKDAYS[time.getDay() - 1]))
  }

  const refresh = () => cells.forEach((fn) => fn())
  refresh()
  time.onPerMinute(refresh)
  if (W.WIDGET_DELEGATE !== undefined) {
    create(W.WIDGET_DELEGATE, { resume_call: refresh })
  }
}

WatchFace({
  build() {
    create(W.FILL_RECT, { x: 0, y: 0, w: px(390), h: px(450), color: 0x000000 })
    create(W.IMG, { x: px(COLON_X), y: px(TIME_Y), src: 'time/colon.png' })

    const need = {
      time: !tryNative('IMG_TIME', nativeTime),
      date: !tryNative('IMG_DATE', nativeDate),
      week: !tryNative('IMG_WEEK', nativeWeek),
    }
    if (need.time || need.date || need.week) {
      fallback(need)
    }
  },

  onInit() {},

  onDestroy() {},
})
