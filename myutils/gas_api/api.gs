function doPost(e) {
  var params = JSON.parse(e.postData.contents);
  var responses = [];
  var debugMessages = [];

  var dataList = params.data;

  // data が配列でなければ配列にラップ
  if (!dataList) {
    return ContentService.createTextOutput(JSON.stringify({
      success: false,
      error: 'No event data provided',
      debug: debugMessages
    })).setMimeType(ContentService.MimeType.JSON);
  }

  if (!Array.isArray(dataList)) {
    dataList = [dataList];
  }

  // --- カレンダーID マッピング設定 ---
  var CALENDARS = {
    "weather": "4c4cc3148140f2b0fb0a965a58c78d1792de8f69e0fa6dddfd724731c7db256d@group.calendar.google.com",
    "1 like": "377182e69aa069411d636148a9a3cb206eca37f5725bd5d1a44db51de9b751f4@group.calendar.google.com",
    "Daily Life": "9ead6636940460164ac0a2e7059d360c7a47d925fb4ed94d205c772ff1515bed@group.calendar.google.com",
    "Diary": "9ed20081d4d8e950f219c1208491f479160fab5a8057870ac48338751a8008e7@group.calendar.google.com"
  };

  // 送信された calendarKey または calendarId を取得（デフォルトは "Daily Life"）
  var calendarKey = params.calendarKey || "Daily Life";
  var targetCalendarId = params.calendarId || CALENDARS[calendarKey] || CALENDARS["Daily Life"];

  var calendar = CalendarApp.getCalendarById(targetCalendarId);
  
  if (!calendar) {
    calendar = CalendarApp.getDefaultCalendar();
    debugMessages.push("Calendar ID not found, using default calendar.");
  } else {
    debugMessages.push("Target calendar obtained: " + calendar.getName() + " (Key/ID: " + targetCalendarId + ")");
  }

  // 色マッピング関数（未指定・Noneの場合は DEFAULT を返す）
  function getEventColor(colorName) {
    if (!colorName) return CalendarApp.EventColor.DEFAULT;

    var map = {
      "PALE_BLUE": CalendarApp.EventColor.PALE_BLUE,
      "GREEN": CalendarApp.EventColor.GREEN,
      "BLUE": CalendarApp.EventColor.BLUE,
      "YELLOW": CalendarApp.EventColor.YELLOW,
      "ORANGE": CalendarApp.EventColor.ORANGE,
      "RED": CalendarApp.EventColor.RED,
      "PURPLE": CalendarApp.EventColor.PURPLE,
      "GRAY": CalendarApp.EventColor.GRAY
    };
    return map[colorName] || CalendarApp.EventColor.DEFAULT;
  }

  dataList.forEach(function(data) {
    try {
      var title = data.title;
      var description = data.description || '';
      var allDay = data.allDay || false;
      var color = getEventColor(data.color);

      var event;
      if (allDay) {
        var startDate = new Date(data.start);
        event = calendar.createAllDayEvent(title, startDate, { description: description });
      } else {
        var startTime = new Date(data.start);
        var endTime = new Date(data.end);

        // 重複チェック
        var existingEvents = calendar.getEvents(startTime, endTime);
        var isDuplicate = existingEvents.some(function(ev) { return ev.getTitle() === title; });

        if (isDuplicate) {
          responses.push({
            success: false,
            error: "Event \"" + title + "\" already exists."
          });
          return;
        }

        event = calendar.createEvent(title, startTime, endTime, { description: description });
      }

      // 色の設定（DEFAULT 以外が指定されている場合のみ設定）
      if (color !== CalendarApp.EventColor.DEFAULT) {
        event.setColor(color);
      }

      responses.push({
        success: true,
        eventId: event.getId()
      });
      debugMessages.push("Event created: " + title + " with ID: " + event.getId());
    } catch (err) {
      responses.push({
        success: false,
        error: err.toString()
      });
      debugMessages.push("Error creating event: " + err.toString());
    }
  });

  return ContentService.createTextOutput(JSON.stringify({
    success: true,
    responses: responses,
    debug: debugMessages
  })).setMimeType(ContentService.MimeType.JSON);
}