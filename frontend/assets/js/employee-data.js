/**
 * AgriPulse Shared Employee Telemetry & KPI Dataset.
 * Provides strict data isolation, dynamic performance score calculation,
 * and operational features like task boards, insights, and report logs.
 */

const EmployeeDataStore = {
  // The 12 primary field officers
  employees: [
    {
      id: "SS-0429",
      name: "Gaikwad Ganesh Balasaheb",
      username: "8465",
      email: "ganesh.gaikwad@srisrisugar.com",
      dept: "Field Operations",
      role: "Senior Field Inspector",
      region: "Atpadi District",
      joined: "Jan 15, 2022",
      status: "Active",
      initials: "GG",
      villagesCount: 14,
      farmerCount: 284,
      metrics: {
        crushingTarget: 88,      // Crushing Target Achievement %
        caneRegTarget: 95,       // Cane Registration Target %
        recoveryTarget: 82,      // Recovery Target %
        farmerMeetings: 90,      // Farmer Meetings %
        kccTarget: 85,           // KCC Target Achievement %
        htAgreement: 80,         // H&T Agreement Target %
        canaraHtLoan: 75,        // Canara H&T Loan Target %
        sangolaHtLoan: 88        // Sangola H&T Loan Target %
      },
      tasks: [
        { id: "t1", title: "Verify cane registration in sector 4", status: "assigned", deadline: "Today, 5:00 PM" },
        { id: "t2", title: "Conduct KCC awareness meet in Atpadi village", status: "completed", deadline: "Yesterday" },
        { id: "t3", title: "Collect pending agreements for Canara H&T", status: "pending", deadline: "In 2 days" },
        { id: "t4", title: "Verify recovery weights at crushing weighbridge", status: "assigned", deadline: "Tomorrow, 10:00 AM" }
      ],
      insights: [
        "Your Recovery Target is below the 85% benchmark. Try scheduling a farmer meeting in Atpadi West to coordinate sugarcane transportation.",
        "Cane Registration Target is nearing completion (95%). Complete the remaining registrations this week.",
        "Pending loan agreements (75%) for Canara H&T are delaying overall H&T processing. Action required."
      ],
      alerts: [
        { id: "a1", type: "warning", message: "Recovery target drops below 85% in Atpadi village.", time: "1 hour ago" },
        { id: "a2", type: "alert", message: "Deadline approaching for Sangola H&T loan submissions.", time: "4 hours ago" },
        { id: "a3", type: "info", message: "KCC Loan documentation successfully verified for 12 farmers.", time: "Yesterday" }
      ],
      weeklyHeatmap: [85, 90, 75, 92, 88, 60, 45] // Monday - Sunday target completion rates %
    },
    {
      id: "SS-0312",
      name: "Rajendra Shrikhande",
      username: "31269",
      email: "rajendra@gmail.com",
      dept: "Field Operations",
      role: "Field Operations Officer",
      region: "Sangola Sector",
      joined: "Mar 10, 2021",
      status: "Active",
      initials: "RS",
      villagesCount: 11,
      farmerCount: 198,
      metrics: {
        crushingTarget: 92,
        caneRegTarget: 88,
        recoveryTarget: 95,
        farmerMeetings: 80,
        kccTarget: 78,
        htAgreement: 85,
        canaraHtLoan: 82,
        sangolaHtLoan: 90
      },
      tasks: [
        { id: "t1", title: "Audit cane registration books", status: "completed", deadline: "Completed" },
        { id: "t2", title: "Organize farmer meeting in Sangola Town", status: "assigned", deadline: "Today, 6:30 PM" },
        { id: "t3", title: "Follow up on KCC applications at Canara Bank", status: "pending", deadline: "Tomorrow" }
      ],
      insights: [
        "Superb Recovery rate (95%) achieved this week, leading all operations officers in the Sangola sector.",
        "KCC Target is currently at 78%. Schedule loan documentation collection to hit the 80% mark."
      ],
      alerts: [
        { id: "a1", type: "info", message: "Cane crushing weights officially logged at weighbridge.", time: "2 hours ago" },
        { id: "a2", type: "warning", message: "3 KCC applications returned due to insufficient land record logs.", time: "1 day ago" }
      ],
      weeklyHeatmap: [90, 85, 92, 94, 96, 50, 40]
    },
    {
      id: "SS-0501",
      name: "Priya Mane",
      username: "8451",
      email: "priya.mane@gmail.com",
      dept: "Farmer Relations",
      role: "Relations Specialist",
      region: "Tasgaon North",
      joined: "Jun 1, 2022",
      status: "Active",
      initials: "PM",
      villagesCount: 9,
      farmerCount: 174,
      metrics: {
        crushingTarget: 75,
        caneRegTarget: 92,
        recoveryTarget: 89,
        farmerMeetings: 95,
        kccTarget: 92,
        htAgreement: 70,
        canaraHtLoan: 65,
        sangolaHtLoan: 72
      },
      tasks: [
        { id: "t1", title: "Conduct farmer meeting regarding loan approvals", status: "assigned", deadline: "Today, 4:00 PM" },
        { id: "t2", title: "Verify cane registration in Tasgaon", status: "completed", deadline: "Completed" }
      ],
      insights: [
        "Outstanding Farmer Engagement (95% Meetings) - keep this up to accelerate KCC submissions.",
        "H&T Agreement target is below baseline (70%). Follow up with cane transport contractors."
      ],
      alerts: [
        { id: "a1", type: "info", message: "Farmer meeting successfully logged in Tasgaon Sector B.", time: "30 mins ago" },
        { id: "a2", type: "warning", message: "Low agreement count on Canara H&T transport contracts.", time: "3 hours ago" }
      ],
      weeklyHeatmap: [70, 75, 80, 88, 92, 95, 80]
    },
    {
      id: "SS-0198",
      name: "Amol Kadam",
      username: "12835",
      email: "amol.kadam@gmail.com",
      dept: "Cane Registration",
      role: "Registrar Officer",
      region: "Sangli West",
      joined: "Nov 5, 2020",
      status: "Active",
      initials: "AK",
      villagesCount: 15,
      farmerCount: 310,
      metrics: {
        crushingTarget: 80,
        caneRegTarget: 96,
        recoveryTarget: 84,
        farmerMeetings: 75,
        kccTarget: 82,
        htAgreement: 92,
        canaraHtLoan: 85,
        sangolaHtLoan: 80
      },
      tasks: [
        { id: "t1", title: "Register new sugarcane fields in Sangli West", status: "assigned", deadline: "Today, 6:00 PM" },
        { id: "t2", title: "Coordinate with Sangola logistics team", status: "pending", deadline: "Tomorrow" }
      ],
      insights: [
        "Registration efficiency is top-tier (96% achieved). Focus on closing outstanding crushing telemetry.",
        "Farmer meeting levels (75%) are currently low. Coordinate weekend meetings to boost KCC loan counts."
      ],
      alerts: [
        { id: "a1", type: "alert", message: "Sugarcane crushing targets entering peak logistics phase.", time: "5 hours ago" }
      ],
      weeklyHeatmap: [80, 82, 85, 90, 92, 70, 50]
    },
    {
      id: "SS-0267",
      name: "Santosh Bhosale",
      username: "29739",
      email: "santosh@gmail.com",
      dept: "Field Operations",
      role: "Field Inspector",
      region: "Atpadi District",
      joined: "Feb 20, 2021",
      status: "Active",
      initials: "SB",
      villagesCount: 8,
      farmerCount: 145,
      metrics: {
        crushingTarget: 85,
        caneRegTarget: 82,
        recoveryTarget: 74,
        farmerMeetings: 85,
        kccTarget: 80,
        htAgreement: 78,
        canaraHtLoan: 70,
        sangolaHtLoan: 82
      },
      tasks: [
        { id: "t1", title: "Check recovery rates at Sector 2 weighbridge", status: "assigned", deadline: "Today, 5:00 PM" },
        { id: "t2", title: "Update cane logs in database", status: "completed", deadline: "Completed" }
      ],
      insights: [
        "Your Recovery target is currently below the average benchmark (74%). Initiate corrective transport scheduling.",
        "KCC achievement is on track at 80%."
      ],
      alerts: [
        { id: "a1", type: "warning", message: "Recovery rate at weighbridge reported low for the last 3 trucks.", time: "2 hours ago" }
      ],
      weeklyHeatmap: [75, 78, 82, 80, 85, 60, 45]
    },
    {
      id: "SS-0344",
      name: "Hemant Markad",
      username: "209",
      email: "hemant@gmail.com",
      dept: "Cane Registration",
      role: "Cane Registration Lead",
      region: "Atpadi District",
      joined: "Aug 12, 2021",
      status: "Active",
      initials: "HM",
      villagesCount: 12,
      farmerCount: 220,
      metrics: {
        crushingTarget: 90,
        caneRegTarget: 94,
        recoveryTarget: 88,
        farmerMeetings: 84,
        kccTarget: 86,
        htAgreement: 88,
        canaraHtLoan: 85,
        sangolaHtLoan: 82
      },
      tasks: [
        { id: "t1", title: "Verify new field registration records", status: "assigned", deadline: "Today, 4:00 PM" },
        { id: "t2", title: "Log crushing telemetries", status: "completed", deadline: "Yesterday" }
      ],
      insights: [
        "All parameters are currently on-track. Crushing and Cane Registration targets are nearing completion.",
        "Keep holding active farmer meetings to secure Canara H&T loan completions."
      ],
      alerts: [
        { id: "a1", type: "info", message: "Weekly cane crushing goals hit early.", time: "1 day ago" }
      ],
      weeklyHeatmap: [88, 90, 92, 94, 90, 70, 60]
    },
    {
      id: "SS-0412",
      name: "Vijaya Patil",
      username: "41283",
      email: "jyoti@srisrisugar.com",
      dept: "Farmer Relations",
      role: "Relations Officer",
      region: "Sangli East",
      joined: "Apr 3, 2022",
      status: "Active",
      initials: "VP",
      villagesCount: 10,
      farmerCount: 190,
      metrics: {
        crushingTarget: 82,
        caneRegTarget: 90,
        recoveryTarget: 86,
        farmerMeetings: 92,
        kccTarget: 88,
        htAgreement: 75,
        canaraHtLoan: 70,
        sangolaHtLoan: 80
      },
      tasks: [
        { id: "t1", title: "Arrange village assembly in Sangli West", status: "assigned", deadline: "Tomorrow, 11:00 AM" },
        { id: "t2", title: "Submit KCC forms to branch manager", status: "completed", deadline: "Completed" }
      ],
      insights: [
        "Great work in Farmer Relations! Meetings reached 92%, resulting in solid KCC target conversions.",
        "H&T Agreements require focus. Ensure contractors sign agreements before crushing shifts."
      ],
      alerts: [
        { id: "a1", type: "info", message: "KCC branch approvals completed for Sector 3.", time: "Yesterday" }
      ],
      weeklyHeatmap: [80, 85, 88, 90, 92, 85, 75]
    },
    {
      id: "SS-0155",
      name: "Dnyaneshwar Jadhav",
      username: "35654",
      email: "annasaheb@gmail.com",
      dept: "Field Operations",
      role: "Field Agent",
      region: "Tasgaon South",
      joined: "Sep 8, 2020",
      status: "On Leave",
      initials: "DJ",
      villagesCount: 6,
      farmerCount: 120,
      metrics: {
        crushingTarget: 60,
        caneRegTarget: 70,
        recoveryTarget: 65,
        farmerMeetings: 60,
        kccTarget: 62,
        htAgreement: 58,
        canaraHtLoan: 50,
        sangolaHtLoan: 60
      },
      tasks: [
        { id: "t1", title: "Submit medical leave log", status: "completed", deadline: "Completed" }
      ],
      insights: [
        "You are currently marked as 'On Leave'. Upon return, synchronize pending cane surveys.",
        "Recovery targets are currently below operational guidelines. Handover pending items to Priya Mane."
      ],
      alerts: [
        { id: "a1", type: "info", message: "Leave log approved by HR department.", time: "2 days ago" }
      ],
      weeklyHeatmap: [20, 20, 20, 20, 10, 0, 0]
    },
    {
      id: "SS-0388",
      name: "Sangita Deshmukh",
      username: "44903",
      email: "jayshree@srisrisugar.com",
      dept: "Cane Registration",
      role: "Registrar Analyst",
      region: "Sangola Sector",
      joined: "Jan 22, 2022",
      status: "Active",
      initials: "SD",
      villagesCount: 13,
      farmerCount: 260,
      metrics: {
        crushingTarget: 91,
        caneRegTarget: 95,
        recoveryTarget: 92,
        farmerMeetings: 88,
        kccTarget: 90,
        htAgreement: 85,
        canaraHtLoan: 80,
        sangolaHtLoan: 92
      },
      tasks: [
        { id: "t1", title: "Input field size datasets for Sangola East", status: "completed", deadline: "Completed" },
        { id: "t2", title: "Audit cane registration submissions", status: "assigned", deadline: "Today, 5:30 PM" }
      ],
      insights: [
        "Highly efficient tracking! All metrics are exceeding standard operations benchmarks.",
        "Sangola H&T Loan target achieved at 92%. Great support on logistics contracts."
      ],
      alerts: [
        { id: "a1", type: "info", message: "Cane survey files synchronized successfully.", time: "3 hours ago" }
      ],
      weeklyHeatmap: [90, 92, 94, 91, 95, 80, 70]
    },
    {
      id: "SS-0421",
      name: "Raju Thorat",
      username: "25366",
      email: "sargarraju@123gmail.com",
      dept: "Field Operations",
      role: "Assistant Field Inspector",
      region: "Tasgaon North",
      joined: "Jul 14, 2022",
      status: "Inactive",
      initials: "RT",
      villagesCount: 7,
      farmerCount: 110,
      metrics: {
        crushingTarget: 50,
        caneRegTarget: 60,
        recoveryTarget: 55,
        farmerMeetings: 50,
        kccTarget: 48,
        htAgreement: 52,
        canaraHtLoan: 45,
        sangolaHtLoan: 50
      },
      tasks: [
        { id: "t1", title: "Submit log checklist", status: "pending", deadline: "Overdue" }
      ],
      insights: [
        "Status is currently Inactive. Contact supervisor to check your regional assignment details.",
        "Operational targets require immediate updates to resume sugarcane tracking tasks."
      ],
      alerts: [
        { id: "a1", type: "warning", message: "Account marked inactive. Target collection paused.", time: "3 days ago" }
      ],
      weeklyHeatmap: [0, 0, 0, 0, 0, 0, 0]
    },
    {
      id: "SS-0305",
      name: "Kavita Shinde",
      username: "44901",
      email: "smita@srisrisugar.com",
      dept: "Farmer Relations",
      role: "Public Relations Officer",
      region: "Sangola Sector",
      joined: "Dec 1, 2020",
      status: "Active",
      initials: "KS",
      villagesCount: 11,
      farmerCount: 210,
      metrics: {
        crushingTarget: 85,
        caneRegTarget: 89,
        recoveryTarget: 91,
        farmerMeetings: 90,
        kccTarget: 86,
        htAgreement: 82,
        canaraHtLoan: 78,
        sangolaHtLoan: 85
      },
      tasks: [
        { id: "t1", title: "Complete farmer interview logs for Sector A", status: "completed", deadline: "Completed" },
        { id: "t2", title: "Verify pending KCC forms in Sangola West", status: "assigned", deadline: "Today, 4:00 PM" }
      ],
      insights: [
        "Excellent farmer coordination! 90% meeting target completed successfully.",
        "Canara H&T loans (78%) require follow-ups to match your Sangola H&T accomplishments (85%)."
      ],
      alerts: [
        { id: "a1", type: "info", message: "Completed loan approval interviews for 14 farmers.", time: "1 day ago" }
      ],
      weeklyHeatmap: [85, 88, 90, 89, 91, 75, 60]
    },
    {
      id: "SS-0477",
      name: "Prakash Kale",
      username: "36793",
      email: "prakashkale@srisrisugar.com",
      dept: "Field Operations",
      role: "Field Supervisor",
      region: "Atpadi District",
      joined: "Oct 9, 2022",
      status: "Active",
      initials: "PK",
      villagesCount: 12,
      farmerCount: 235,
      metrics: {
        crushingTarget: 83,
        caneRegTarget: 92,
        recoveryTarget: 80,
        farmerMeetings: 85,
        kccTarget: 83,
        htAgreement: 88,
        canaraHtLoan: 80,
        sangolaHtLoan: 85
      },
      tasks: [
        { id: "t1", title: "Inspect local crushing weighbridges", status: "assigned", deadline: "Today, 5:00 PM" },
        { id: "t2", title: "Verify farmer land registrations", status: "completed", deadline: "Completed" }
      ],
      insights: [
        "Crushing targets are strong at 83%. Focus on raising recovery ratings.",
        "KCC and H&T Agreements are well aligned. Complete pending Canara loans to reach full metrics."
      ],
      alerts: [
        { id: "a1", type: "info", message: "Survey logs reviewed and approved by Cane Yard.", time: "12 hours ago" }
      ],
      weeklyHeatmap: [82, 85, 80, 92, 88, 70, 50]
    }
  ],

  // Base Fallback for newly logged-in/unmatched users (e.g. Admin Test, Common User)
  fallbackTemplate: {
    id: "SS-TEMP",
    name: "Field Officer Account",
    username: "field_officer",
    email: "field@srisrisugar.com",
    dept: "Field Operations",
    role: "Operational Field Specialist",
    region: "Atpadi District",
    joined: "May 2, 2024",
    status: "Active",
    initials: "FO",
    villagesCount: 10,
    farmerCount: 150,
    metrics: {
      crushingTarget: 85,
      caneRegTarget: 90,
      recoveryTarget: 80,
      farmerMeetings: 85,
      kccTarget: 80,
      htAgreement: 75,
      canaraHtLoan: 70,
      sangolaHtLoan: 80
    },
    tasks: [
      { id: "t1", title: "Verify cane registrations in active village grids", status: "assigned", deadline: "Today, 5:00 PM" },
      { id: "t2", title: "Schedule farmer meeting", status: "completed", deadline: "Completed" }
    ],
    insights: [
      "Keep logging daily crushing and recovery telemetries to maintain a high performance ranking score.",
      "Farmer meetings (85%) are strong. Follow up on pending KCC applications."
    ],
    alerts: [
      { id: "a1", type: "info", message: "System initialized. Welcome to the AgriPulse Operations Dashboard.", time: "Just now" }
    ],
    weeklyHeatmap: [80, 85, 80, 90, 85, 60, 40]
  },

  // Dynamic Performance Score Calculator
  calculateScore(emp) {
    const m = emp.metrics;
    // Formula: 40% Crushing + 20% Recovery + 20% Meetings + 20% KCC
    const score = (0.40 * m.crushingTarget) + (0.20 * m.recoveryTarget) + (0.20 * m.farmerMeetings) + (0.20 * m.kccTarget);
    return Math.round(score * 10) / 10;
  },

  // Dynamically find and bind logged-in user to their dataset
  getLoggedInEmployee() {
    if (typeof AgriAuth === 'undefined') return this.fallbackTemplate;
    const session = AgriAuth.getSession();
    if (!session) return this.fallbackTemplate;

    const username = (session.username || "").toLowerCase().trim();
    const name = (session.name || "").toLowerCase().trim();
    const isStaff = !!session.isStaff;

    // First attempt: Match by exact database username (e.g. "8465", "31269")
    let found = this.employees.find(e => e.username === username);

    // Second attempt: Match by exact username search
    if (!found) {
      found = this.employees.find(e => e.username.toLowerCase() === username);
    }

    // Third attempt: Match by name
    if (!found) {
      found = this.employees.find(e => {
        const lowerName = e.name.toLowerCase();
        return lowerName === name || lowerName.includes(name) || name.includes(lowerName);
      });
    }

    // If still not found, construct a custom profile dynamically based on session details
    if (!found) {
      const initials = name.trim().split(/\s+/).slice(0, 2).map(w => w[0] || '').join("").toUpperCase() || "FO";
      const customized = {
        ...this.fallbackTemplate,
        name: session.name && session.name !== "None" ? session.name : session.username,
        username: session.username,
        email: session.email && session.email !== "None" ? session.email : "field@srisrisugar.com",
        initials: initials,
        role: isStaff ? "Staff Supervisor" : "Field Specialist",
        id: "SS-" + (1000 + Math.floor(Math.random() * 9000))
      };
      return customized;
    }

    return found;
  }
};
