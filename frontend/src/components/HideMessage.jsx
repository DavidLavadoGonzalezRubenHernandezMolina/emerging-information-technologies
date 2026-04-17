import { useState, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { useDropzone } from "react-dropzone"
import { Upload, ImageIcon, Lock, Download, X, CheckCircle } from "lucide-react"

export default function HideMessage() {
  const [image, setImage] = useState(null)
  const [preview, setPreview] = useState(null)
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const onDrop = useCallback((acceptedFiles) => {
    const file = acceptedFiles[0]
    if (file) {
      setImage(file)
      setPreview(URL.createObjectURL(file))
      setResult(null)
      setError(null)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "image/*": [] },
    maxFiles: 1
  })

  const handleSubmit = async () => {
    if (!image || !message.trim()) {
      setError("Necesitas una imagen y un mensaje")
      return
    }

    setLoading(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append("image", image)
      formData.append("message", message)

      const response = await fetch("http://localhost:8000/hide", {
        method: "POST",
        body: formData
      })

      if (!response.ok) throw new Error("Error al procesar la imagen")

      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      setResult(url)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleClear = () => {
    setImage(null)
    setPreview(null)
    setMessage("")
    setResult(null)
    setError(null)
  }

  return (
    <div className="space-y-4">

      {/* Card principal */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-3xl p-6"
      >
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center">
            <Lock className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">Ocultar Mensaje</h2>
            <p className="text-gray-400 text-sm">Embebe un mensaje secreto en una imagen</p>
          </div>
        </div>

        {/* Dropzone */}
        <div
          {...getRootProps()}
          className={`relative border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all duration-300 ${
            isDragActive
              ? "border-violet-400 bg-violet-500/10"
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
                className="relative"
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
                    <ImageIcon className="w-6 h-6 text-violet-400" />
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

        {/* Mensaje */}
        <div className="mt-4">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Mensaje secreto
          </label>
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Escribe el mensaje que quieres ocultar..."
            rows={3}
            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 text-sm focus:outline-none focus:border-violet-500/50 focus:bg-white/8 transition-all duration-200 resize-none"
          />
          <p className="text-gray-500 text-xs mt-1 text-right">{message.length} caracteres</p>
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
            disabled={loading || !image || !message.trim()}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="flex-1 bg-gradient-to-r from-violet-500 to-indigo-600 text-white font-medium py-3 rounded-xl disabled:opacity-40 disabled:cursor-not-allowed transition-opacity duration-200 flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full"
                />
                Procesando...
              </>
            ) : (
              <>
                <Lock className="w-4 h-4" />
                Ocultar mensaje
              </>
            )}
          </motion.button>

          {(image || message) && (
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

      {/* Resultado */}
      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="bg-emerald-500/5 border border-emerald-500/20 rounded-3xl p-6"
          >
            <div className="flex items-center gap-3 mb-4">
              <CheckCircle className="w-5 h-5 text-emerald-400" />
              <h3 className="font-semibold text-emerald-400">Mensaje ocultado con éxito</h3>
            </div>
            <img
              src={result}
              alt="Resultado"
              className="max-h-48 mx-auto rounded-xl object-contain mb-4"
            />
            <motion.a
              href={result}
              download="imagen_con_mensaje_oculto.png"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="flex items-center justify-center gap-2 w-full bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 text-emerald-400 font-medium py-3 rounded-xl transition-all duration-200"
            >
              <Download className="w-4 h-4" />
              Descargar imagen
            </motion.a>
          </motion.div>
        )}
      </AnimatePresence>

    </div>
  )
}