import { useState, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { useDropzone } from "react-dropzone"
import { Upload, ImageIcon, Search, X, Shield, AlertTriangle, Info } from "lucide-react"
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts"

export default function ForensicReport() {
  const [image, setImage] = useState(null)
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [report, setReport] = useState(null)
  const [error, setError] = useState(null)

  const onDrop = useCallback((acceptedFiles) => {
    const file = acceptedFiles[0]
    if (file) {
      setImage(file)
      setPreview(URL.createObjectURL(file))
      setReport(null)
      setError(null)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "image/*": [] },
    maxFiles: 1
  })

  const handleSubmit = async () => {
    if (!image) {
      setError("Necesitas seleccionar una imagen")
      return
    }

    setLoading(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append("image", image)

      const response = await fetch("http://localhost:8000/forensics", {
        method: "POST",
        body: formData
      })

      if (!response.ok) throw new Error("Error al analizar la imagen")

      const data = await response.json()
      setReport(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleClear = () => {
    setImage(null)
    setPreview(null)
    setReport(null)
    setError(null)
  }

  const getSuspicionColor = (score) => {
    if (score >= 0.95) return "text-rose-400"
    if (score >= 0.75) return "text-orange-400"
    if (score >= 0.50) return "text-yellow-400"
    return "text-emerald-400"
  }

  const getSuspicionBg = (score) => {
    if (score >= 0.95) return "bg-rose-500/10 border-rose-500/20"
    if (score >= 0.75) return "bg-orange-500/10 border-orange-500/20"
    if (score >= 0.50) return "bg-yellow-500/10 border-yellow-500/20"
    return "bg-emerald-500/10 border-emerald-500/20"
  }

  const buildHistogramData = (values) => {
    if (!values) return []
    const buckets = Array(16).fill(0)
    values.forEach(v => {
      const idx = Math.min(Math.floor(v / 16), 15)
      buckets[idx]++
    })
    return buckets.map((count, i) => ({
      rango: `${i * 16}`,
      count
    }))
  }

  return (
    <div className="space-y-4">

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-3xl p-6"
      >
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-rose-500 to-pink-600 flex items-center justify-center">
            <Search className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">Análisis Forense</h2>
            <p className="text-gray-400 text-sm">Inspección profunda de metadatos y estadísticas LSB</p>
          </div>
        </div>

        {/* Dropzone */}
        <div
          {...getRootProps()}
          className={`relative border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all duration-300 ${
            isDragActive
              ? "border-rose-400 bg-rose-500/10"
              : preview
              ? "border-white/20 bg-white/5"
              : "border-white/10 hover:border-white/20 hover:bg-white/5"
          }`}
        >
          <input {...getInputProps()} />
          <AnimatePresence mode="wait">
            {preview ? (
              <motion.div
                key="preview"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
              >
                <img
                  src={preview}
                  alt="Preview"
                  className="max-h-48 mx-auto rounded-xl object-contain"
                />
                <p className="text-gray-400 text-sm mt-3">{image?.name}</p>
              </motion.div>
            ) : (
              <motion.div
                key="upload"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <div className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center mx-auto mb-3">
                  {isDragActive ? (
                    <ImageIcon className="w-6 h-6 text-rose-400" />
                  ) : (
                    <Upload className="w-6 h-6 text-gray-400" />
                  )}
                </div>
                <p className="text-gray-300 font-medium">
                  {isDragActive ? "Suelta la imagen aquí" : "Arrastra una imagen o haz clic"}
                </p>
                <p className="text-gray-500 text-sm mt-1">PNG, JPG, WEBP</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Error */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mt-4 bg-rose-500/10 border border-rose-500/20 rounded-xl px-4 py-3 text-rose-400 text-sm"
            >
              {error}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Botones */}
        <div className="flex gap-3 mt-5">
          <motion.button
            onClick={handleSubmit}
            disabled={loading || !image}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="flex-1 bg-gradient-to-r from-rose-500 to-pink-600 text-white font-medium py-3 rounded-xl disabled:opacity-40 disabled:cursor-not-allowed transition-opacity duration-200 flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full"
                />
                Analizando...
              </>
            ) : (
              <>
                <Search className="w-4 h-4" />
                Analizar imagen
              </>
            )}
          </motion.button>

          {image && (
            <motion.button
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              onClick={handleClear}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="w-12 h-12 bg-white/5 border border-white/10 rounded-xl flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-all duration-200"
            >
              <X className="w-4 h-4" />
            </motion.button>
          )}
        </div>
      </motion.div>

      {/* Informe */}
      <AnimatePresence>
        {report && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="space-y-4"
          >

            {/* Puntuación de sospecha */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.1 }}
              className={`border rounded-3xl p-6 ${getSuspicionBg(report.lsb_analysis?.suspicion_score)}`}
            >
              <div className="flex items-center gap-3 mb-3">
                <Shield className={`w-5 h-5 ${getSuspicionColor(report.lsb_analysis?.suspicion_score)}`} />
                <h3 className={`font-semibold ${getSuspicionColor(report.lsb_analysis?.suspicion_score)}`}>
                  Veredicto forense
                </h3>
              </div>
              <p className={`text-2xl font-bold mb-1 ${getSuspicionColor(report.lsb_analysis?.suspicion_score)}`}>
                {report.lsb_analysis?.interpretation}
              </p>
              <p className="text-gray-400 text-sm">
                Puntuación de sospecha: <span className="text-white font-medium">{(report.lsb_analysis?.suspicion_score * 100).toFixed(1)}%</span>
              </p>

              {/* Barra de progreso */}
              <div className="mt-4 h-2 bg-white/10 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${report.lsb_analysis?.suspicion_score * 100}%` }}
                  transition={{ delay: 0.3, duration: 0.8, ease: "easeOut" }}
                  className={`h-full rounded-full ${
                    report.lsb_analysis?.suspicion_score >= 0.95 ? "bg-rose-400" :
                    report.lsb_analysis?.suspicion_score >= 0.75 ? "bg-orange-400" :
                    report.lsb_analysis?.suspicion_score >= 0.50 ? "bg-yellow-400" :
                    "bg-emerald-400"
                  }`}
                />
              </div>
            </motion.div>

            {/* Info básica */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.2 }}
              className="bg-white/5 border border-white/10 rounded-3xl p-6"
            >
              <div className="flex items-center gap-3 mb-4">
                <Info className="w-5 h-5 text-gray-400" />
                <h3 className="font-semibold">Información de la imagen</h3>
              </div>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: "Archivo", value: report.filename },
                  { label: "Formato", value: report.format || "PNG" },
                  { label: "Modo", value: report.mode },
                  { label: "Dimensiones", value: `${report.size?.width} × ${report.size?.height}px` },
                  { label: "Píxeles analizados", value: report.lsb_analysis?.total_pixels_analyzed?.toLocaleString() },
                  { label: "LSB unos / ceros", value: `${report.lsb_analysis?.lsb_ones?.toLocaleString()} / ${report.lsb_analysis?.lsb_zeros?.toLocaleString()}` },
                ].map((item, i) => (
                  <motion.div
                    key={item.label}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.3 + i * 0.05 }}
                    className="bg-white/5 rounded-xl p-3"
                  >
                    <p className="text-gray-500 text-xs mb-1">{item.label}</p>
                    <p className="text-white text-sm font-medium truncate">{item.value}</p>
                  </motion.div>
                ))}
              </div>
            </motion.div>

            {/* Histograma LSB */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.3 }}
              className="bg-white/5 border border-white/10 rounded-3xl p-6"
            >
              <div className="flex items-center gap-3 mb-4">
                <AlertTriangle className="w-5 h-5 text-gray-400" />
                <h3 className="font-semibold">Distribución canal Rojo (LSB)</h3>
              </div>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={buildHistogramData(report.histogram?.R)}>
                  <XAxis dataKey="rango" tick={{ fill: '#6b7280', fontSize: 10 }} />
                  <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} />
                  <Tooltip
                    contentStyle={{ background: '#111', border: '1px solid #333', borderRadius: '8px' }}
                    labelStyle={{ color: '#fff' }}
                    itemStyle={{ color: '#a78bfa' }}
                  />
                  <Bar dataKey="count" fill="#7c3aed" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </motion.div>

            {/* EXIF */}
            {report.exif && Object.keys(report.exif).length > 0 && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.4 }}
                className="bg-white/5 border border-white/10 rounded-3xl p-6"
              >
                <div className="flex items-center gap-3 mb-4">
                  <Info className="w-5 h-5 text-gray-400" />
                  <h3 className="font-semibold">Metadatos EXIF</h3>
                </div>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {Object.entries(report.exif).map(([key, value], i) => (
                    <motion.div
                      key={key}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.4 + i * 0.03 }}
                      className="flex justify-between items-start gap-4 py-2 border-b border-white/5 last:border-0"
                    >
                      <span className="text-gray-400 text-xs shrink-0">{key}</span>
                      <span className="text-white text-xs text-right truncate max-w-[60%]">{value}</span>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            )}

          </motion.div>
        )}
      </AnimatePresence>

    </div>
  )
}