import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Shield, EyeOff, Eye, Search } from "lucide-react"
import HideMessage from "./components/HideMessage"
import ExtractMessage from "./components/ExtractMessage"
import ForensicReport from "./components/ForensicReport"

const tabs = [
  { id: "hide", label: "Ocultar", icon: EyeOff, color: "from-violet-500 to-indigo-500" },
  { id: "extract", label: "Extraer", icon: Eye, color: "from-emerald-500 to-teal-500" },
  { id: "forensics", label: "Análisis Forense", icon: Search, color: "from-rose-500 to-pink-500" },
]

export default function App() {
  const [activeTab, setActiveTab] = useState("hide")

  return (
    <div className="min-h-screen bg-[#050505] text-white">

      {/* Fondo con gradiente animado */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-violet-500 rounded-full mix-blend-multiply filter blur-[128px] opacity-10 animate-float" />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-indigo-500 rounded-full mix-blend-multiply filter blur-[128px] opacity-10 animate-float" style={{ animationDelay: '2s' }} />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-rose-500 rounded-full mix-blend-multiply filter blur-[128px] opacity-5 animate-float" style={{ animationDelay: '4s' }} />
      </div>

      {/* Header */}
      <motion.header
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        className="relative z-10 pt-16 pb-8 text-center px-4"
      >
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
          className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 mb-6 shadow-lg shadow-violet-500/25"
        >
          <Shield className="w-8 h-8 text-white" />
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.8 }}
          className="text-5xl font-bold tracking-tight mb-3"
        >
          The{" "}
          <span className="bg-gradient-to-r from-violet-400 to-indigo-400 bg-clip-text text-transparent">
            Matrix
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5, duration: 0.8 }}
          className="text-gray-400 text-lg max-w-md mx-auto"
        >
          Herramienta de esteganografía y análisis forense de imágenes
        </motion.p>
      </motion.header>

      {/* Tabs */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6, duration: 0.6 }}
        className="relative z-10 flex justify-center gap-2 px-4 mb-12"
      >
        <div className="flex bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-1.5">
          {tabs.map((tab) => {
            const Icon = tab.icon
            const isActive = activeTab === tab.id
            return (
              <motion.button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`relative flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-colors duration-200 ${
                  isActive ? "text-white" : "text-gray-400 hover:text-gray-200"
                }`}
                whileTap={{ scale: 0.97 }}
              >
                {isActive && (
                  <motion.div
                    layoutId="activeTab"
                    className={`absolute inset-0 bg-gradient-to-r ${tab.color} rounded-xl opacity-90`}
                    transition={{ type: "spring", stiffness: 400, damping: 30 }}
                  />
                )}
                <span className="relative z-10 flex items-center gap-2">
                  <Icon className="w-4 h-4" />
                  {tab.label}
                </span>
              </motion.button>
            )
          })}
        </div>
      </motion.div>

      {/* Contenido */}
      <main className="relative z-10 max-w-3xl mx-auto px-4 pb-24">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 20, filter: "blur(4px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            exit={{ opacity: 0, y: -20, filter: "blur(4px)" }}
            transition={{ duration: 0.3 }}
          >
            {activeTab === "hide" && <HideMessage />}
            {activeTab === "extract" && <ExtractMessage />}
            {activeTab === "forensics" && <ForensicReport />}
          </motion.div>
        </AnimatePresence>
      </main>

      {/* Footer */}
      <motion.footer
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1, duration: 0.8 }}
        className="relative z-10 text-center pb-8 text-gray-600 text-sm"
      >
        Desarrollado por David Lavado González & Rubén Hernández Molina
      </motion.footer>

    </div>
  )
}