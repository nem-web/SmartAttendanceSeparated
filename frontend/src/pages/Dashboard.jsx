import React from "react";
import { Link } from "react-router-dom";

export default function Dashboard(){
  return (
    <div className="w-full mx-auto space-y-6 bg-[var(--bg-primary)]">
      {/* upper part */}
      <div className="main flex items-center justify-around w-full">
        <div className="left-main">
          <h2 className="text-4xl">Teacher Dashboard</h2>
          <span>Overview of today's attendance and upcoming classes</span>
        </div>

        <div className="right-main flex items-center justify-center">
          <a href="/download">Download Report</a>
          <a href="/start-attendance">Start Attendance</a>
        </div>
        
      </div>

      {/* cards */}
      <div className="grid bg-[var(--bg-card)] grid-cols-2">
          <div className="left-card p-4 flex items-center justify-around w-[60%]">
            <div className="name">
              <h3>Good morning, Alex</h3>
              <p>Monday, Spetember 23 08:45</p>
              <p>Next Class - Grade 10 A 09:00  Room 203</p>
            </div>
            <div className="camera">
              <p>Face Recognition ready</p>
              <a href="/attendance-start">Start Attendance session</a>
              <p>Camera and permission checked</p>
            </div>
          </div>
          <div className="right-card p-4 items-center w-[40%]">
            <h3>Attendance Trends</h3>
          </div>
      </div>

      
    </div>
  );
}
