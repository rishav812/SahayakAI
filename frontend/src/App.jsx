import React from 'react';
import { 
  MessageSquare, 
  ExternalLink, 
  GitMerge, 
  DollarSign, 
  HelpCircle, 
  Calendar, 
  UserCheck, 
  Sparkles,
  Layers,
  ArrowRight,
  ShieldAlert,
  Bot
} from 'lucide-react';

const GithubIcon = ({ className = "w-4 h-4" }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
    <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
  </svg>
);

const LinkedinIcon = ({ className = "w-4 h-4" }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
    <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/>
  </svg>
);


export default function App() {
  const agents = [
    {
      name: "Supervisor",
      description: "Reads every incoming message and routes it to the right agent(s), merging responses if a query touches more than one topic.",
      icon: GitMerge,
      badge: "Orchestrator",
      color: "from-blue-500/20 to-indigo-500/20 text-blue-400 border-blue-500/30"
    },
    {
      name: "Admissions Agent",
      description: "Looks up real fee data via a tool call, no hallucinated numbers.",
      icon: DollarSign,
      badge: "Tool Calling",
      color: "from-emerald-500/20 to-teal-500/20 text-emerald-400 border-emerald-500/30"
    },
    {
      name: "FAQ Agent",
      description: "Answers syllabus/policy questions using RAG over real institute documents.",
      icon: HelpCircle,
      badge: "RAG Engine",
      color: "from-purple-500/20 to-pink-500/20 text-purple-400 border-purple-500/30"
    },
    {
      name: "Scheduling Agent",
      description: "Books demo classes, and offers real alternative slots if the requested one is taken.",
      icon: Calendar,
      badge: "Calendar Sync",
      color: "from-amber-500/20 to-orange-500/20 text-amber-400 border-amber-500/30"
    },
    {
      name: "Human Handoff",
      description: "Escalates to a real counsellor with the full conversation transcript when needed.",
      icon: UserCheck,
      badge: "Escalation",
      color: "from-rose-500/20 to-red-500/20 text-rose-400 border-rose-500/30"
    }
  ];

  const techStack = [
    { name: "LangGraph", desc: "Multi-Agent Graph State" },
    { name: "FastAPI", desc: "High-Perf Python Backend" },
    { name: "PostgreSQL", desc: "State & Checkpointing" },
    { name: "ChromaDB", desc: "Vector Search RAG" },
    { name: "OpenAI", desc: "LLM & Embeddings" },
    { name: "Twilio", desc: "WhatsApp API Engine" },
    { name: "Docker", desc: "Containerized Runtime" },
    { name: "Fly.io", desc: "Edge Deployment" }
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-emerald-500 selection:text-slate-950 flex flex-col justify-between relative overflow-hidden">
      
      {/* Background Subtle Gradient Blobs */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-[500px] pointer-events-none opacity-20 bg-[radial-gradient(circle_at_top,_var(--tw-gradient-stops))] from-emerald-500/30 via-slate-900/10 to-transparent blur-3xl" />
      
      <header className="w-full max-w-5xl mx-auto px-6 pt-8 pb-4 flex items-center justify-between z-10">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shadow-sm shadow-emerald-500/20">
            <Bot className="w-5 h-5" />
          </div>
          <span className="font-extrabold text-xl tracking-tight text-white">Sahayak<span className="text-emerald-400">AI</span></span>
        </div>
        <a 
          href="https://github.com/rishav812/SahayakAI" 
          target="_blank" 
          rel="noreferrer"
          className="flex items-center gap-2 text-xs font-medium text-slate-400 hover:text-white transition-colors bg-slate-900/80 hover:bg-slate-800 px-3.5 py-1.5 rounded-full border border-slate-800"
        >
          <GithubIcon className="w-3.5 h-3.5" />
          <span>GitHub</span>
        </a>
      </header>

      <main className="w-full max-w-5xl mx-auto px-4 sm:px-6 py-8 flex-1 space-y-20 z-10">
        
        {/* 1. Hero Section */}
        <section className="text-center pt-6 pb-2 max-w-3xl mx-auto space-y-6">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold tracking-wide uppercase">
            <Sparkles className="w-3.5 h-3.5" />
            <span>WhatsApp-First Multi-Agent Architecture</span>
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-white tracking-tight leading-[1.15]">
            Sahayak<span className="text-emerald-400">AI</span>
          </h1>

          <p className="text-base sm:text-lg lg:text-xl text-slate-300 leading-relaxed font-normal max-w-2xl mx-auto">
            Coaching institutes in Tier-2/3 India lose admissions every day — not because of bad teaching, but because no one replies to a WhatsApp query fast enough. SahayakAI is a WhatsApp-first multi-agent assistant that handles real parent/student conversations — fee questions, demo bookings, policy doubts — in Hindi and English.
          </p>
        </section>

        {/* 2. Demo Video Section */}
        <section className="space-y-4">
          <div className="text-center space-y-1">
            <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400">System Demo</h2>
            <p className="text-sm text-slate-400">Watch how SahayakAI coordinates agents seamlessly</p>
          </div>
          
          <div className="max-w-4xl mx-auto rounded-2xl overflow-hidden glass-card p-2 sm:p-3 shadow-2xl border border-slate-800/80">
            <div className="relative aspect-video rounded-xl bg-slate-900 overflow-hidden border border-slate-800/60 group">
              <video 
                controls 
                className="w-full h-full object-cover rounded-lg"
                poster="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='100%' height='100%' viewBox='0 0 800 450'><rect width='100%' height='100%' fill='%230f172a'/><text x='50%' y='48%' font-family='sans-serif' font-size='24' font-weight='bold' fill='%2310b981' text-anchor='middle'>SahayakAI Live Demo</text><text x='50%' y='56%' font-family='sans-serif' font-size='14' fill='%2364748b' text-anchor='middle'>Click play to watch video (/demo.mp4)</text></svg>"
              >
                <source src="/demo.mp4" type="video/mp4" />
                Your browser does not support the video tag.
              </video>
            </div>
          </div>
        </section>

        {/* 3. Try It Live Section */}
        <section className="glass-card rounded-2xl p-8 sm:p-10 text-center max-w-3xl mx-auto border border-emerald-500/20 relative overflow-hidden emerald-glow">
          <div className="space-y-6 relative z-10">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              <MessageSquare className="w-6 h-6" />
            </div>

            <div className="space-y-2">
              <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">Try it live</h2>
              <p className="text-slate-300 text-sm sm:text-base max-w-xl mx-auto">
                This isn't a canned demo — message the bot yourself and get a real response from the live backend.
              </p>
            </div>

            <div className="pt-2">
              <a
                href="https://wa.me/14155238886?text=join%20chamber-across"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center justify-center gap-3 px-8 py-4 text-base font-bold text-slate-950 bg-emerald-400 hover:bg-emerald-300 active:bg-emerald-500 rounded-xl transition-all shadow-lg shadow-emerald-500/25 hover:shadow-emerald-500/40 hover:-translate-y-0.5"
              >
                <span>Try SahayakAI on WhatsApp</span>
                <ArrowRight className="w-5 h-5" />
              </a>
            </div>

            <p className="text-xs text-slate-400 pt-1">
              Powered by Twilio WhatsApp Sandbox — first message may take a moment to connect.
            </p>
          </div>
        </section>

        {/* 4. How It's Structured Section */}
        <section className="space-y-8">
          <div className="text-center space-y-2">
            <div className="inline-flex items-center gap-2 text-emerald-400 text-xs font-semibold uppercase tracking-wider">
              <Layers className="w-4 h-4" />
              <span>Multi-Agent System</span>
            </div>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">How it's structured</h2>
            <p className="text-slate-400 text-sm sm:text-base max-w-xl mx-auto">
              LangGraph-powered stateful agent workflow designed for deterministic reliability.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {agents.map((agent, index) => {
              const IconComponent = agent.icon;
              return (
                <div 
                  key={index} 
                  className={`glass-card glass-card-hover p-6 rounded-2xl flex flex-col justify-between border ${index === 0 ? 'lg:col-span-2' : ''}`}
                >
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className={`p-3 rounded-xl border bg-slate-900/80 ${agent.color}`}>
                        <IconComponent className="w-5 h-5" />
                      </div>
                      <span className="text-[11px] font-semibold px-2.5 py-1 rounded-md bg-slate-800 text-slate-300 border border-slate-700">
                        {agent.badge}
                      </span>
                    </div>

                    <div>
                      <h3 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
                        {agent.name}
                      </h3>
                      <p className="text-slate-300 text-sm leading-relaxed mt-2">
                        {agent.description}
                      </p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* 5. Tech Stack Footer */}
        <section className="pt-8 border-t border-slate-800/80 space-y-10">
          <div className="space-y-4 text-center">
            <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400">Built With Production Tech</h3>
            <div className="flex flex-wrap items-center justify-center gap-2 sm:gap-3 max-w-3xl mx-auto">
              {techStack.map((tech, i) => (
                <div 
                  key={i} 
                  className="px-3.5 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800 text-slate-200 text-xs sm:text-sm font-medium hover:border-slate-700 hover:text-white transition-colors"
                >
                  {tech.name}
                </div>
              ))}
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-6 text-xs text-slate-400">
            <div className="flex items-center gap-2">
              <span>Developer: <a href="https://github.com/rishav812" target="_blank" rel="noreferrer" className="text-slate-200 hover:text-emerald-400 font-semibold transition-colors">Rishav Kumar</a></span>
            </div>

            <div className="flex items-center gap-4">
              <a 
                href="https://github.com/rishav812/SahayakAI" 
                target="_blank" 
                rel="noreferrer"
                className="flex items-center gap-1.5 hover:text-emerald-400 transition-colors"
              >
                <GithubIcon className="w-4 h-4" />
                <span>GitHub Repository</span>
              </a>
              <span className="text-slate-700">•</span>
              <a 
                href="https://www.linkedin.com/in/iamrishav/" 
                target="_blank" 
                rel="noreferrer"
                className="flex items-center gap-1.5 hover:text-emerald-400 transition-colors"
              >
                <LinkedinIcon className="w-4 h-4" />
                <span>LinkedIn</span>
              </a>
            </div>
          </div>
        </section>

      </main>
      
      <footer className="w-full text-center py-6 text-[11px] text-slate-600 border-t border-slate-900 z-10">
        SahayakAI Portfolio Demo Page &copy; {new Date().getFullYear()} — Built for Tier-2/3 India Coaching Operations
      </footer>
    </div>
  );
}
