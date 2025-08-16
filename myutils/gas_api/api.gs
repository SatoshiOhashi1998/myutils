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

  var calendar = CalendarApp.getDefaultCalendar();
  debugMessages.push("Default calendar obtained.");

  // 色マッピング関数
  function getEventColor(colorName) {
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
        var isDuplicate = existingEvents.some(ev => ev.getTitle() === title);

        if (isDuplicate) {
          responses.push({
            success: false,
            error: `Event "${title}" already exists.`
          });
          return; // 次のイベントへ
        }

        event = calendar.createEvent(title, startTime, endTime, { description: description });
      }

      event.setColor(color);

      responses.push({
        success: true,
        eventId: event.getId()
      });
      debugMessages.push(`Event created: ${title} with ID: ${event.getId()}`);
    } catch (err) {
      responses.push({
        success: false,
        error: err.message
      });
      debugMessages.push(`Error creating event: ${err.message}`);
    }
  });

  return ContentService.createTextOutput(JSON.stringify({
    success: true,
    responses: responses,
    debug: debugMessages
  })).setMimeType(ContentService.MimeType.JSON);
}
