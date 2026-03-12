import React, { useState, useEffect } from 'react';
import './Calendar.css'; // We will create this file for specific calendar styles

export default function Calendar({ events = [], topics = [] }) {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [activeTopics, setActiveTopics] = useState(new Set(topics));

  // Initialize activeTopics when topics change
  useEffect(() => {
    setActiveTopics(prev => {
      const next = new Set(prev);
      topics.forEach(t => next.add(t));
      return next;
    });
  }, [topics]);

  const toggleTopic = (topic) => {
    setActiveTopics(prev => {
      const next = new Set(prev);
      if (next.has(topic)) {
        next.delete(topic);
      } else {
        next.add(topic);
      }
      return next;
    });
  };

  const getTopicColorClass = (topic) => {
    if (topic === "Uncategorized") return "topic-color-0";
    const index = topics.indexOf(topic);
    // Cycle through 1 to 5
    return `topic-color-${(Math.max(0, index) % 5) + 1}`;
  };

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const firstDayOfMonth = new Date(year, month, 1).getDay(); // 0 is Sunday

  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];

  const prevMonth = () => {
    setCurrentDate(new Date(year, month - 1, 1));
  };

  const nextMonth = () => {
    setCurrentDate(new Date(year, month + 1, 1));
  };

  const setToday = () => {
    setCurrentDate(new Date());
  };

  // Helper to get ISO week number
  const getWeekNumber = (d) => {
    const date = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
    const dayNum = date.getUTCDay() || 7;
    date.setUTCDate(date.getUTCDate() + 4 - dayNum);
    const yearStart = new Date(Date.UTC(date.getUTCFullYear(),0,1));
    return Math.ceil((((date - yearStart) / 86400000) + 1)/7);
  };

  // Filter events by active topics
  const filteredEvents = events.filter(e => activeTopics.has(e.topic));

  // Generate grid cells
  const totalCells = Math.ceil((daysInMonth + firstDayOfMonth) / 7) * 7;
  const weeks = [];
  let currentWeek = [];

  for (let i = 0; i < totalCells; i++) {
    const dayNumber = i - firstDayOfMonth + 1;
    let isCurrentMonth = true;
    let dateObj;

    if (dayNumber <= 0) {
      isCurrentMonth = false;
      const prevMonthDays = new Date(year, month, 0).getDate();
      dateObj = new Date(year, month - 1, prevMonthDays + dayNumber);
    } else if (dayNumber > daysInMonth) {
      isCurrentMonth = false;
      dateObj = new Date(year, month + 1, dayNumber - daysInMonth);
    } else {
      dateObj = new Date(year, month, dayNumber);
    }

    const isToday = new Date().toDateString() === dateObj.toDateString();

    const dayEvents = filteredEvents.filter(e => {
        if (!e.date) return false;
        const eDate = new Date(e.date);
        return eDate.getDate() === dateObj.getDate() && 
               eDate.getMonth() === dateObj.getMonth() && 
               eDate.getFullYear() === dateObj.getFullYear();
    });

    currentWeek.push({
      date: dateObj,
      isCurrentMonth,
      isToday,
      dayNumber: dateObj.getDate(),
      events: dayEvents
    });

    if (currentWeek.length === 7) {
      weeks.push(currentWeek);
      currentWeek = [];
    }
  }

  return (
    <div className="fc-container">
      {/* Sidebar */}
      <div className="fc-sidebar glass-panel">
        <button className="fc-create-btn small-button primary" type="button">
          <span className="plus-icon">+</span> Create
        </button>

        <div className="fc-mini-cal">
          <div className="fc-sidebar-title">{monthNames[month]} {year}</div>
          {/* A simple mock of mini calendar for aesthetic */}
          <div className="fc-mini-grid">
            {['S','M','T','W','T','F','S'].map((d, i) => <div key={i} className="fc-mini-dayname">{d}</div>)}
            {Array.from({length: 42}).map((_, i) => {
              const d = i - firstDayOfMonth + 1;
              const isCurr = d > 0 && d <= daysInMonth;
              const isTod = isCurr && new Date().toDateString() === new Date(year, month, d).toDateString();
              return (
                <div key={i} className={`fc-mini-day ${isCurr ? '' : 'muted'} ${isTod ? 'today' : ''}`}>
                  {isCurr ? d : ''}
                </div>
              );
            })}
          </div>
        </div>

        <div className="fc-sidebar-section">
          <div className="fc-sidebar-title">My Topics</div>
          {topics.map(topic => (
            <label key={topic} className="fc-sidebar-item">
              <input 
                type="checkbox" 
                className="fc-checkbox" 
                checked={activeTopics.has(topic)}
                onChange={() => toggleTopic(topic)}
              />
              <span className={`fc-checkbox-custom ${getTopicColorClass(topic)}`}></span>
              {topic}
            </label>
          ))}
        </div>
      </div>

      {/* Main Calendar Area */}
      <div className="fc-main glass-panel">
        <div className="fc-header">
          <div className="fc-header-left">
            <button className="small-button" onClick={setToday}>Today</button>
            <div className="fc-nav-arrows">
              <button className="icon-button" onClick={prevMonth}>&lt;</button>
              <button className="icon-button" onClick={nextMonth}>&gt;</button>
            </div>
            <h2 className="fc-title">{monthNames[month]} {year}</h2>
          </div>
          <div className="fc-header-right">
            <select className="fc-view-select small-button">
              <option>Month</option>
              <option>Week</option>
            </select>
          </div>
        </div>

        <div className="fc-grid-wrapper">
          <div className="fc-weekdays">
            <div className="fc-weekday-spacer"></div> {/* For week numbers */}
            {['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'].map((day, idx) => (
              <div key={day} className="fc-weekday">
                {day}
              </div>
            ))}
          </div>

          <div className="fc-body">
            {weeks.map((week, wIdx) => {
              const weekNum = getWeekNumber(week[0].date);
              return (
                <div key={wIdx} className="fc-week-row">
                  <div className="fc-week-number">
                    <span>{weekNum}</span>
                  </div>
                  {week.map((day, dIdx) => (
                    <div key={dIdx} className={`fc-day-cell ${day.isCurrentMonth ? '' : 'fc-day-other-month'}`}>
                      <div className={`fc-day-number ${day.isToday ? 'fc-day-today' : ''}`}>
                        {day.dayNumber === 1 && day.isCurrentMonth ? `${monthNames[day.date.getMonth()].slice(0,3)} 1` : (day.dayNumber === 1 ? `${monthNames[day.date.getMonth()].slice(0,3)} 1` : day.dayNumber)}
                      </div>
                      <div className="fc-day-events">
                        {day.events.map((evt, idx) => (
                          <div key={idx} className={`fc-event ${getTopicColorClass(evt.topic)}`} title={evt.title}>
                            {evt.title}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
