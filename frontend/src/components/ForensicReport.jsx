import { useState, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { useDropzone } from "react-dropzone"
import {
  Upload, ImageIcon, Search, X, Shield, FileWarning,
  Activity, Info, AlertTriangle, CheckCircle2, FileCode, Type
} from "lucide-react"

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

  const verdictStyle = (score) => {
    if (score >= 0.75) return {
      text: "text-rose-400",
      bg: "bg-rose-500/10 border-rose-500/20",
      bar: "bg-rose-400",
      icon: AlertTriangle
    }
    if (score >= 0.45) return {
      text: "text-orange-400",
      bg: "bg-orange-500/10 border-orange-500/20",
      bar: "bg-orange-400",
      icon: FileWarning
    }
    if (score >= 0.20) return {
      text: "text-yellow-400",
      bg: "bg-yellow-500/10 border-yellow-500/20",
      bar: "bg-yellow-400",
      icon: Shield
    }
    return {
      text: "text-emerald-400",
      bg: "bg-emerald-500/10 border-emerald-500/20",
      bar: "bg-emerald-400",
      icon: CheckCircle2
    }
  }

  const Metric = ({ label, value, description }) => {
    const pct = Math.max(0, Math.min(1, value)) * 100
    return (
      <div className="bg-white/5 rounded-xl p-3">
        <div className="flex justify-between items-baseline mb-1">
          <span className="text-gray-400 text-xs">{label}</span>
          <span className="text-white text-sm font-medium tabular-nums">
            {value.toFixed(3)}
          </span>
        </div>
        <div className="h-1 bg-white/10 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.6, ease: "easeOut" }}
            className={`h-full ${
              pct >= 75 ? "bg-rose-400" :
              pct >= 45 ? "bg-orange-400" :
              pct >= 20 ? "bg-yellow-400" :
              "bg-emerald-400"
            }`}
          />
        </div>
        {description && (
          <p className="text-gray-500 text-xs mt-1.5 leading-snug">{description}</p>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-4">

      {/* Panel de carga */}
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
            <p className="text-gray-400 text-sm">
              Detección multicapa: estructura, firmas, cadenas y estadística
            </p>
          </div>
        </div>

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
                <img src={preview} alt="Preview" className="max-h-48 mx-auto rounded-xl object-contain" />
                <p className="text-gray-400 text-sm mt-3">{image?.name}</p>
              </motion.div>
            ) : (
              <motion.div key="upload" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <div className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center mx-auto mb-3">
                  {isDragActive ? <ImageIcon className="w-6 h-6 text-rose-400" /> : <Upload className="w-6 h-6 text-gray-400" />}
                </div>
                <p className="text-gray-300 font-medium">
                  {isDragActive ? "Suelta la imagen aquí" : "Arrastra una imagen o haz clic"}
                </p>
                <p className="text-gray-500 text-sm mt-1">PNG, JPG, WEBP</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

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
        {report && (() => {
          const style = verdictStyle(report.final_score)
          const VerdictIcon = style.icon
          const fa = report.file_analysis || {}
          const pa = report.pixel_analysis || {}
          const embedded = fa.embedded_findings || []
          const asciiStrings = fa.printable_strings_samples || []

          return (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="space-y-4"
            >

              {/* Veredicto principal */}
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.1 }}
                className={`border rounded-3xl p-6 ${style.bg}`}
              >
                <div className="flex items-center gap-3 mb-3">
                  <VerdictIcon className={`w-5 h-5 ${style.text}`} />
                  <h3 className={`font-semibold ${style.text}`}>Veredicto</h3>
                </div>
                <p className={`text-2xl font-bold mb-1 ${style.text}`}>{report.verdict}</p>
                <p className="text-gray-400 text-sm">
                  Puntuación final:{" "}
                  <span className="text-white font-medium">
                    {(report.final_score * 100).toFixed(1)}%
                  </span>
                </p>
                <div className="mt-4 h-2 bg-white/10 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${report.final_score * 100}%` }}
                    transition={{ delay: 0.3, duration: 0.8, ease: "easeOut" }}
                    className={`h-full rounded-full ${style.bar}`}
                  />
                </div>
              </motion.div>

              {/* Archivos embebidos detectados (Capa B) */}
              {embedded.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.15 }}
                  className="bg-rose-500/10 border border-rose-500/30 rounded-3xl p-6"
                >
                  <div className="flex items-center gap-3 mb-4">
                    <FileCode className="w-5 h-5 text-rose-400" />
                    <h3 className="font-semibold text-rose-400">
                      Archivos embebidos detectados
                    </h3>
                  </div>
                  <div className="space-y-2">
                    {embedded.map((item, i) => (
                      <div key={i} className="bg-rose-500/10 rounded-xl p-3 border border-rose-500/20">
                        <div className="flex justify-between items-center">
                          <span className="text-rose-300 font-medium text-sm">
                            {item.signature}
                          </span>
                          <span className="text-rose-400/70 text-xs tabular-nums">
                            offset {item.offset}
                          </span>
                        </div>
                        <p className="text-rose-400/50 text-xs mt-1 font-mono">
                          magic bytes: {item.bytes}
                        </p>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}

              {/* Cadenas ASCII sospechosas (Capa C) */}
              {asciiStrings.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.17 }}
                  className="bg-orange-500/10 border border-orange-500/30 rounded-3xl p-6"
                >
                  <div className="flex items-center gap-3 mb-4">
                    <Type className="w-5 h-5 text-orange-400" />
                    <h3 className="font-semibold text-orange-400">
                      Cadenas de texto detectadas
                    </h3>
                  </div>
                  <div className="space-y-2">
                    {asciiStrings.map((s, i) => (
                      <div key={i} className="bg-orange-500/10 rounded-xl p-3 border border-orange-500/20">
                        <div className="flex justify-between items-center mb-1">
                          <span className="text-orange-400/70 text-xs tabular-nums">
                            offset {s.offset}
                          </span>
                          <span className="text-orange-400/70 text-xs">
                            {s.length} bytes
                          </span>
                        </div>
                        <p className="text-orange-300 text-xs font-mono break-all leading-relaxed">
                          {s.preview}
                          {s.length > 80 && "..."}
                        </p>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}

              {/* Capa 1: Análisis del archivo */}
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.2 }}
                className="bg-white/5 border border-white/10 rounded-3xl p-6"
              >
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <FileWarning className="w-5 h-5 text-gray-400" />
                    <h3 className="font-semibold">Capa 1 · Estructura del archivo</h3>
                  </div>
                  <span className="text-xs text-gray-500 tabular-nums">
                    score {fa.file_layer_score?.toFixed(3)}
                  </span>
                </div>

                {fa.file_layer_reasons?.length > 0 && (
                  <div className="mb-4 space-y-2">
                    {fa.file_layer_reasons.map((r, i) => (
                      <div key={i} className="flex items-start gap-2 bg-rose-500/10 border border-rose-500/20 rounded-xl px-3 py-2">
                        <AlertTriangle className="w-4 h-4 text-rose-400 mt-0.5 shrink-0" />
                        <span className="text-rose-300 text-sm">{r}</span>
                      </div>
                    ))}
                  </div>
                )}

                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-white/5 rounded-xl p-3">
                    <p className="text-gray-500 text-xs mb-1">Tamaño de archivo</p>
                    <p className="text-white text-sm font-medium">
                      {fa.file_size_bytes?.toLocaleString()} B
                    </p>
                  </div>
                  <div className="bg-white/5 rounded-xl p-3">
                    <p className="text-gray-500 text-xs mb-1">Bytes por píxel</p>
                    <p className="text-white text-sm font-medium">{fa.bytes_per_pixel}</p>
                  </div>
                  {"trailing_bytes" in fa && (
                    <div className="bg-white/5 rounded-xl p-3">
                      <p className="text-gray-500 text-xs mb-1">Bytes tras EOF</p>
                      <p className={`text-sm font-medium ${fa.trailing_bytes > 16 ? "text-rose-400" : "text-white"}`}>
                        {fa.trailing_bytes}
                      </p>
                    </div>
                  )}
                  <div className="bg-white/5 rounded-xl p-3">
                    <p className="text-gray-500 text-xs mb-1">Firmas embebidas</p>
                    <p className={`text-sm font-medium ${fa.embedded_count > 0 ? "text-rose-400" : "text-white"}`}>
                      {fa.embedded_count ?? 0}
                    </p>
                  </div>
                  <div className="bg-white/5 rounded-xl p-3">
                    <p className="text-gray-500 text-xs mb-1">Cadenas ASCII raras</p>
                    <p className={`text-sm font-medium ${fa.printable_strings_count > 0 ? "text-orange-400" : "text-white"}`}>
                      {fa.printable_strings_count ?? 0}
                    </p>
                  </div>
                  {"total_chunks" in fa && (
                    <div className="bg-white/5 rounded-xl p-3">
                      <p className="text-gray-500 text-xs mb-1">Chunks PNG</p>
                      <p className="text-white text-sm font-medium">
                        {fa.total_chunks}
                        {fa.unknown_chunks?.length > 0 && (
                          <span className="text-rose-400"> (+{fa.unknown_chunks.length} raros)</span>
                        )}
                      </p>
                    </div>
                  )}
                </div>
              </motion.div>

              {/* Capa 2: Análisis estadístico */}
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.3 }}
                className="bg-white/5 border border-white/10 rounded-3xl p-6"
              >
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <Activity className="w-5 h-5 text-gray-400" />
                    <h3 className="font-semibold">Capa 2 · Estadística de píxeles</h3>
                  </div>
                  <span className="text-xs text-gray-500 tabular-nums">
                    score {pa.pixel_layer_score?.toFixed(3)}
                  </span>
                </div>

                <div className="space-y-3">
                  <Metric
                    label="Chi-square attack"
                    value={pa.chi_square ?? 0}
                    description="Westfeld-Pfitzmann. Detecta pares LSB artificialmente equilibrados."
                  />
                  <Metric
                    label="RS analysis"
                    value={pa.rs_analysis ?? 0}
                    description="Fridrich-Goljan-Du. Estima la longitud relativa del mensaje oculto."
                  />
                  <Metric
                    label="Ruptura de correlación LSB"
                    value={pa.lsb_spatial_break ?? 0}
                    description="Compara correlación espacial del LSB vs el segundo bit."
                  />
                </div>

                <div className="grid grid-cols-2 gap-3 mt-4">
                  <div className="bg-white/5 rounded-xl p-3">
                    <p className="text-gray-500 text-xs mb-1">Ratio de unos en LSB</p>
                    <p className="text-white text-sm font-medium">
                      {pa.lsb_ratio_ones?.toFixed(4)}
                    </p>
                  </div>
                  <div className="bg-white/5 rounded-xl p-3">
                    <p className="text-gray-500 text-xs mb-1">Dimensiones</p>
                    <p className="text-white text-sm font-medium">
                      {report.size?.width} × {report.size?.height}
                    </p>
                  </div>
                  <div className="bg-white/5 rounded-xl p-3">
                    <p className="text-gray-500 text-xs mb-1">Bloques 32×32 baja correlación</p>
                    <p className="text-white text-sm font-medium tabular-nums">
                      {pa.local_blocks_low_correlation ?? 0} / {pa.local_blocks_total ?? 0}
                    </p>
                  </div>
                  <div className="bg-white/5 rounded-xl p-3">
                    <p className="text-gray-500 text-xs mb-1">Correlación mediana LSB</p>
                    <p className="text-white text-sm font-medium">
                      {pa.local_median_correlation?.toFixed(4)}
                    </p>
                  </div>
                </div>
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
                    {Object.entries(report.exif).map(([key, value]) => (
                      <div key={key} className="flex justify-between items-start gap-4 py-2 border-b border-white/5 last:border-0">
                        <span className="text-gray-400 text-xs shrink-0">{key}</span>
                        <span className="text-white text-xs text-right truncate max-w-[60%]">{value}</span>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}

            </motion.div>
          )
        })()}
      </AnimatePresence>

    </div>
  )
}