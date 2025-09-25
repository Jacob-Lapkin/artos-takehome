import { useState, useCallback, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { api } from './api'

// Icons
function IconUpload(props){return(
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" className={props.className||'h-5 w-5'}>
    <path strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2M12 12V4m0 0 3 3m-3-3-3 3"/>
  </svg>)}

function IconSparkles(props){return(
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" className={props.className||'h-5 w-5'}>
    <path strokeWidth="1.5" strokeLinecap="round" d="M12 3l1.8 3.8L18 8.6l-3.2 2.5L15.6 15 12 13.2 8.4 15l.8-3.9L6 8.6l4.2-1.8L12 3z"/>
  </svg>)}

function IconCheck(props){return(
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" className={props.className||'h-5 w-5'}>
    <path strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7"/>
  </svg>)}

function IconDownload(props){return(
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" className={props.className||'h-5 w-5'}>
    <path strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" d="M12 3v12m0 0 4-4m-4 4-4-4M5 21h14"/>
  </svg>)}

function IconChevron(props){return(
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" className={props.className||'h-4 w-4'}>
    <path strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" d="M9 6l6 6-6 6"/>
  </svg>)}

// Loading components
function LoadingDots({ label='Working' }){
  return (
    <span className="inline-flex items-center gap-2 text-white">
      <span className="relative inline-flex -space-x-1">
        <span className="h-2 w-2 rounded-full bg-blue-400 animate-bounce [animation-delay:-0.2s]"></span>
        <span className="h-2 w-2 rounded-full bg-blue-300 animate-bounce [animation-delay:0s]"></span>
        <span className="h-2 w-2 rounded-full bg-blue-200 animate-bounce [animation-delay:0.2s]"></span>
      </span>
      <span className="font-medium">{label}…</span>
    </span>
  )
}

function Skeleton({ lines=3 }){
  return (
    <div className="animate-pulse">
      {Array.from({length: lines}).map((_,i) => (
        <div key={i} className={`h-3 rounded bg-gray-200 ${i? 'mt-3':''} ${i===lines-1? 'w-2/3':'w-full'}`}></div>
      ))}
    </div>
  )
}

function ConicSpinner({ label }){
  return (
    <div className="flex items-center gap-3">
      <div className="relative h-6 w-6">
        <span className="absolute inset-0 rounded-full bg-[conic-gradient(var(--tw-gradient-stops))] from-blue-400 via-blue-600 to-blue-400 animate-spin"></span>
        <span className="absolute inset-1 rounded-full bg-slate-800"></span>
      </div>
      {label && <span className="text-white font-medium">{label}…</span>}
    </div>
  )}

// Header component
function Header({ embedded = false }){
  const outer = embedded
    ? 'relative z-10 bg-transparent'
    : 'sticky top-0 z-20 bg-slate-900/90 backdrop-blur border-b border-slate-700'
  return (
    <header className={outer}>
      <div className={embedded ? 'px-8 lg:px-16 h-16 flex items-center justify-between' : 'container mx-auto px-6 h-16 flex items-center justify-between'}>
        <div className="flex items-center gap-3">
          <div className="relative">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 shadow-lg">
              <IconSparkles className="h-5 w-5 text-white" />
            </span>
            <div className="absolute -top-1 -right-1 h-3 w-3 bg-blue-400 rounded-full animate-pulse"></div>
          </div>
          <span className="font-bold text-xl text-white">Artos ICF</span>
        </div>
        <nav className="hidden sm:flex items-center gap-8 text-sm">
          <a className="text-slate-300 hover:text-white transition-colors duration-200 font-medium" href="#">Home</a>
          <a className="text-slate-300 hover:text-white transition-colors duration-200 font-medium" href="#">Docs</a>
          <a className="text-slate-300 hover:text-white transition-colors duration-200 font-medium" href="#">Support</a>
        </nav>
      </div>
    </header>
  )
}

// Hero component
function Hero(){
  return (
    <section className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-blue-900 relative overflow-hidden">
      {/* Animated background elements */}
      <div className="absolute inset-0">
        <div className="absolute top-10 left-10 w-72 h-72 bg-blue-500/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute bottom-10 right-10 w-96 h-96 bg-blue-400/10 rounded-full blur-3xl animate-pulse [animation-delay:1s]"></div>
        <div className="absolute top-1/2 left-1/3 w-64 h-64 bg-blue-600/10 rounded-full blur-3xl animate-pulse [animation-delay:2s]"></div>
      </div>

      {/* Grid pattern */}
      <div
        className="absolute inset-0 opacity-10 pointer-events-none"
        style={{
          backgroundImage:
            `linear-gradient(rgba(59,130,246,0.3) 1px, transparent 1px),`+
            `linear-gradient(90deg, rgba(59,130,246,0.3) 1px, transparent 1px)`,
          backgroundSize: '60px 60px'
        }}
      />

      <Header embedded />
      <div className="relative container mx-auto px-6 lg:px-8 pt-16 pb-24" style={{maxWidth:'85rem'}}>
        <div className="grid md:grid-cols-2 items-center gap-16">
          <div className="relative z-10">
            <div className="inline-flex items-center gap-3 px-4 py-2 bg-blue-500/20 backdrop-blur rounded-full border border-blue-400/30 mb-8">
              <IconSparkles className="h-4 w-4 text-blue-400" />
              <span className="text-sm font-medium text-blue-300">AI-Powered ICF Generator</span>
            </div>
            <h1 className="text-5xl lg:text-6xl font-bold tracking-tight text-white leading-tight">
              Turn <span className="bg-gradient-to-r from-blue-400 to-blue-600 bg-clip-text text-transparent">Protocols</span> into Patient‑Friendly ICFs
            </h1>
            <p className="mt-6 text-xl text-slate-300 leading-relaxed max-w-xl">
              Upload a clinical protocol PDF and our AI extracts the facts to draft clear, consent‑ready sections you can download as a DOCX.
            </p>
          </div>
          <div className="relative">
            <img
              src="/src/assets/hero_image.png"
              alt="Clinical consent discussion"
              className="w-full h-96 object-contain"
            />
          </div>
        </div>
      </div>
    </section>
  )
}

// Footer component
function Footer(){
  return (
    <footer className="bg-slate-900 border-t border-slate-700">
      <div className="container mx-auto px-6 lg:px-8 py-12">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <div className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-blue-600">
              <IconSparkles className="h-4 w-4 text-white" />
            </div>
            <div>
              <span className="font-bold text-white text-lg">Artos ICF</span>
              <p className="text-slate-400 text-sm">© {new Date().getFullYear()} · AI-powered consent generation</p>
            </div>
          </div>
          <nav className="flex items-center gap-8 text-sm">
            <a href="/docs" target="_blank" className="text-slate-400 hover:text-white transition-colors duration-200 font-medium">API Docs</a>
            <a href="#" className="text-slate-400 hover:text-white transition-colors duration-200 font-medium">Privacy</a>
            <a href="#" className="text-slate-400 hover:text-white transition-colors duration-200 font-medium">Terms</a>
          </nav>
        </div>
      </div>
    </footer>
  )
}

// Stepper component
const steps = [
  { key: 'upload', label: 'Upload' },
  { key: 'ingest', label: 'Ingest' },
  { key: 'generate', label: 'Generate' },
  { key: 'preview', label: 'Preview' },
]

function Stepper({ stage }){
  const index = steps.findIndex(s => s.key === stage)
  return (
    <ol className="mb-12 grid grid-cols-4 gap-4">
      {steps.map((s, i) => {
        const isDone = i < index
        const isActive = i === index
        return (
          <li key={s.key} className={`relative rounded-2xl border-2 p-4 text-center transition-all duration-300 ${
            isActive
              ? 'border-blue-400 bg-gradient-to-br from-blue-50 to-blue-100 shadow-lg scale-105'
              : isDone
              ? 'border-blue-300 bg-gradient-to-br from-blue-50 to-white shadow-md'
              : 'border-slate-300 bg-white hover:border-slate-400 hover:shadow-sm'
          }`}>
            {isActive && (
              <div className="absolute -top-1 -left-1 w-3 h-3 bg-blue-400 rounded-full animate-ping"></div>
            )}
            <div className="flex items-center justify-center gap-3">
              {isDone ? (
                <div className="flex items-center justify-center w-6 h-6 bg-blue-500 rounded-full">
                  <IconCheck className="h-3 w-3 text-white"/>
                </div>
              ) : (
                <span className={`h-3 w-3 rounded-full transition-all duration-200 ${
                  isActive ? 'bg-blue-500 animate-pulse shadow-lg' : 'bg-slate-300'
                }`}/>
              )}
              <span className={`text-sm font-semibold ${
                isActive || isDone ? 'text-blue-700' : 'text-slate-600'
              }`}>{s.label}</span>
            </div>
          </li>
        )
      })}
    </ol>
  )
}

// Upload Dropzone component
function UploadDropzone({ onSelect, file }) {
  const inputRef = useRef(null)
  const [dragOver, setDragOver] = useState(false)

  const openPicker = () => inputRef.current?.click()
  const handleFiles = useCallback((files) => {
    const f = files?.[0]
    if (!f) return
    onSelect?.(f)
  }, [onSelect])

  return (
    <div>
      <div
        className={[
          'relative border-3 border-dashed rounded-3xl px-8 py-12 text-center cursor-pointer transition-all duration-300 overflow-hidden shadow-lg',
          dragOver
            ? 'border-blue-400 bg-gradient-to-br from-blue-50 to-blue-100 scale-102 shadow-xl'
            : 'border-slate-300 bg-gradient-to-br from-slate-50 to-slate-100 hover:border-blue-300 hover:shadow-xl hover:scale-101'
        ].join(' ')}
        onClick={openPicker}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files) }}
      >
        {/* Background decoration */}
        <div className="absolute top-4 right-4 w-16 h-16 bg-blue-100 rounded-full opacity-50"></div>
        <div className="absolute bottom-4 left-4 w-12 h-12 bg-blue-200 rounded-full opacity-30"></div>

        <div className="relative z-10">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-blue-600 shadow-lg">
            <IconUpload className="h-8 w-8 text-white" />
          </div>
          <div className="text-slate-800 text-xl font-bold mb-2">Upload your protocol PDF</div>
          <p className="text-slate-500 text-base">Drag & drop or click to browse (.pdf / .docx)</p>

          <div className="mt-8 min-h-[32px]">
            {file && (
              <div className="mx-auto inline-flex items-center gap-3 rounded-2xl border-2 border-blue-200 bg-gradient-to-r from-blue-50 to-blue-100 px-4 py-2 text-sm">
                <div className="flex items-center justify-center w-5 h-5 bg-blue-500 rounded-full">
                  <IconCheck className="h-3 w-3 text-white" />
                </div>
                <span className="truncate max-w-[60ch] font-medium text-blue-800">{file.name}</span>
                <span className="text-blue-600 font-medium">· {Math.max(1, Math.round(file.size/1024))} KB</span>
              </div>
            )}
          </div>

          <button type="button" className="mt-6 inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-3 text-white font-semibold shadow-lg hover:from-blue-700 hover:to-blue-800 hover:shadow-xl transition-all duration-200 transform hover:scale-105">
            <IconUpload className="h-4 w-4" />
            Choose File
          </button>
        </div>

        <input
          ref={inputRef}
          type="file"
          className="hidden"
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>
    </div>
  )
}

// Accordion component
function Accordion({ title, children, defaultOpen=false }){
  const [open, setOpen] = useState(!!defaultOpen)
  return (
    <div className="rounded-2xl border-2 border-slate-200 bg-gradient-to-br from-slate-50 to-slate-100 shadow-md hover:shadow-lg transition-all duration-200">
      <button onClick={() => setOpen(v=>!v)} className="w-full flex items-center justify-between px-6 py-4 hover:bg-slate-50 rounded-t-2xl transition-colors duration-200">
        <h3 className="text-lg font-bold text-slate-800">{title}</h3>
        <div className={`p-1 rounded-lg bg-slate-100 transition-all duration-200 ${open ? 'bg-blue-100 rotate-90' : 'hover:bg-slate-200'}`}>
          <IconChevron className={`h-4 w-4 transition-colors duration-200 ${open ? 'text-blue-600' : 'text-slate-500'}`} />
        </div>
      </button>
      {open && (
        <div className="px-6 pb-6 border-t border-slate-200">
          <div className="pt-4">
            {children}
          </div>
        </div>
      )}
    </div>
  )
}

// Markdown with Citations component
const CITE_RE = /\[\[[^\]]+\]\]/g

function remarkInlineCitations() {
  return (tree) => {
    function transform(node){
      if (node && Array.isArray(node.children)){
        const newChildren = []
        for (const child of node.children){
          if (child.type === 'text' && typeof child.value === 'string' && CITE_RE.test(child.value)){
            const parts = child.value.split(/(\[\[[^\]]+\]\])/g).filter(Boolean)
            for (const part of parts){
              if (CITE_RE.test(part)){
                newChildren.push({ type: 'inlineCode', value: part })
              } else {
                newChildren.push({ type: 'text', value: part })
              }
            }
          } else {
            transform(child)
            newChildren.push(child)
          }
        }
        node.children = newChildren
      }
    }
    transform(tree)
  }
}

function CitationPill({ text }){
  const raw = text.replace(/^\[\[|\]\]$/g,'').trim()
  const title = raw
  const m = raw.match(/p\.\s*(\d+)/i)
  const page = m ? m[1] : null
  const sectionMatch = raw.match(/Section:\s*([^\]]+)/i)
  const section = sectionMatch ? sectionMatch[1].trim() : null
  const short = [page?`p.${page}`:null, section?section:null].filter(Boolean).join(' • ')
  return (
    <span className="group relative inline-flex items-center">
      <span className="ml-1 inline-flex items-center rounded-full border border-gray-300 bg-gray-50 px-2 text-xs text-gray-700">
        {short || raw}
      </span>
      <span className="pointer-events-none absolute left-0 top-full mt-1 hidden whitespace-pre rounded-md border border-gray-200 bg-white px-2 py-1 text-xs text-gray-700 shadow-md group-hover:block">{title}</span>
    </span>
  )
}

function MarkdownWithCitations({ content }){
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm, remarkInlineCitations]}
      components={{
        h1: ({node, ...props}) => <h1 className="text-xl font-semibold text-gray-900" {...props} />,
        h2: ({node, ...props}) => <h2 className="text-lg font-semibold text-gray-900 mt-4" {...props} />,
        p: ({node, ...props}) => <p className="text-gray-700 leading-7" {...props} />,
        li: ({node, ...props}) => <li className="text-gray-700 leading-7" {...props} />,
        code: ({inline, children, ...props}) => {
          const val = String(children||'')
          if (inline && CITE_RE.test(val)) return <CitationPill text={val} />
          return inline
            ? <code className="rounded bg-gray-100 px-1 py-0.5 text-[0.85em]" {...props}>{children}</code>
            : <pre className="rounded-md bg-gray-900 p-3 text-white overflow-auto" {...props}><code>{children}</code></pre>
        },
        ul: ({node, ...props}) => <ul className="list-disc pl-5 space-y-1" {...props} />,
        ol: ({node, ...props}) => <ol className="list-decimal pl-5 space-y-1" {...props} />,
      }}
    >{content || ''}</ReactMarkdown>
  )
}

export default function App() {
  const [file, setFile] = useState(null)
  const [fileId, setFileId] = useState(null)
  const [indexMeta, setIndexMeta] = useState(null)
  const [runId, setRunId] = useState(null)
  const [sections, setSections] = useState(null)
  const [busy, setBusy] = useState(false)
  const [step, setStep] = useState('idle') // idle|upload|ingest|generate|preview
  const [error, setError] = useState(null)

  const reset = () => {
    setFile(null); setFileId(null); setIndexMeta(null); setRunId(null); setSections(null)
    setBusy(false); setStep('idle'); setError(null)
  }

  async function handleStart() {
    if (!file) return
    setError(null)
    setBusy(true)
    try {
      setStep('upload')
      const up = await api.uploadFile(file)
      setFileId(up.file_id)

      setStep('ingest')
      const ing = await api.ingest(up.file_id)
      setIndexMeta(ing)

      setStep('generate')
      // Use combined generate + refine flow
      const gen = await api.generateRefine(up.file_id)
      setRunId(gen.run_id)
      setSections(gen.sections)
      setStep('preview')
    } catch (e) {
      setError(e.message || 'Unexpected error')
      setStep('idle')
    } finally {
      setBusy(false)
    }
  }

  async function handleDownload() {
    if (!runId) return
    try {
      const blob = await api.downloadDocx(runId)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `ICF_${runId}.docx`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (e) {
      setError(e.message || 'Failed to download DOCX')
    }
  }

  async function handleDownloadLogs() {
    if (!runId) return
    try {
      const logs = await api.getRunLogs(runId)
      const blob = new Blob([JSON.stringify(logs, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `ICF_${runId}_logs.json`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (e) {
      setError(e.message || 'Failed to download logs')
    }
  }

  return (
    <div className="font-sans min-h-screen bg-white">
      <Hero />
      <main className="container mx-auto px-6 pb-24 -mt-32 relative z-10">
        {error && (
          <div className="mb-8 rounded-2xl border-2 border-red-300 bg-gradient-to-r from-red-50 to-red-100 p-6 shadow-lg">
            <div className="flex items-center gap-3">
              <div className="w-6 h-6 bg-red-500 rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-bold">!</span>
              </div>
              <span className="text-red-800 font-semibold">{error}</span>
            </div>
          </div>
        )}

        <Stepper stage={step === 'idle' ? 'upload' : step} />

        {/* Uploader / Action */}
        {step === 'idle' && (
          <section className="grid gap-8 md:grid-cols-2">
            <UploadDropzone onSelect={setFile} file={file} />
            <div className="rounded-3xl border-2 border-slate-200 p-8 bg-gradient-to-br from-slate-50 to-slate-100 shadow-lg">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-8 h-8 bg-blue-100 rounded-xl flex items-center justify-center">
                  <IconCheck className="h-4 w-4 text-blue-600" />
                </div>
                <h2 className="text-xl font-bold text-slate-800">Selected File</h2>
              </div>
              <div className="bg-slate-100 rounded-2xl p-4 mb-6">
                <p className="text-slate-600 text-base">
                  {file ? (
                    <span className="flex items-center gap-2">
                      <span className="font-semibold text-slate-800">{file.name}</span>
                      <span className="text-slate-500">({Math.round(file.size/1024)} KB)</span>
                    </span>
                  ) : (
                    <span className="text-slate-400 italic">No file selected yet</span>
                  )}
                </p>
              </div>
              <button
                disabled={!file || busy}
                onClick={handleStart}
                className={`w-full inline-flex items-center justify-center gap-3 rounded-2xl px-6 py-4 text-white font-bold text-lg shadow-lg transition-all duration-200 transform ${
                  !file || busy
                    ? 'bg-slate-400 cursor-not-allowed'
                    : 'bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 hover:scale-105 hover:shadow-xl'
                }`}
              >
                {busy ? (
                  <LoadingDots label="Processing" />
                ) : (
                  <>
                    <IconSparkles className="h-5 w-5" />
                    Generate ICF Sections
                  </>
                )}
              </button>
            </div>
          </section>
        )}

        {/* Progress status */}
        {['upload','ingest','generate'].includes(step) && (
          <section className="rounded-3xl border-2 border-slate-200 p-8 bg-gradient-to-br from-slate-800 to-slate-900 shadow-xl">
            <div className="flex flex-col items-center text-center">
              <ConicSpinner label={{upload:'Uploading', ingest:'Analyzing', generate:'Generating'}[step]} />
              {file && (
                <div className="mt-6 inline-flex items-center gap-3 rounded-2xl border border-slate-600 bg-slate-700 px-4 py-2 text-sm">
                  <IconCheck className={`h-4 w-4 ${fileId? 'text-blue-400':'text-slate-400'}`} />
                  <span className="truncate max-w-[60ch] text-white font-medium">{file.name}</span>
                  {fileId && <span className="text-slate-300 text-xs bg-slate-600 px-2 py-1 rounded-full">uploaded</span>}
                </div>
              )}
              {fileId && (
                <div className="mt-4 p-4 bg-slate-700 rounded-xl">
                  <p className="text-slate-300 text-sm">
                    File ID: <span className="font-mono text-blue-400">{fileId}</span>
                  </p>
                </div>
              )}
              {step !== 'upload' && !sections && (
                <div className="mt-8 w-full max-w-md"><Skeleton lines={4}/></div>
              )}
            </div>
          </section>
        )}

        {/* Preview */}
        {step === 'preview' && sections && (
          <section className="space-y-6 mt-16">
           <br/>
            <div className="grid gap-6">
              {Object.entries(sections).map(([name, obj]) => (
                <Accordion key={name} title={name} defaultOpen={false}>
                  <div className="prose prose-slate max-w-none">
                    <MarkdownWithCitations content={obj?.text || ''} />
                  </div>
                </Accordion>
              ))}
            </div>
            <div className="flex items-center justify-between rounded-3xl border-2 border-slate-200 bg-gradient-to-r from-slate-50 to-slate-100 p-8 shadow-lg mt-8">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl flex items-center justify-center">
                  <IconCheck className="h-6 w-6 text-white" />
                </div>
                <div>
                  <div className="text-slate-800 font-bold text-lg">Generation Complete</div>
                  <div className="font-mono text-slate-600 text-sm bg-slate-100 px-3 py-1 rounded-lg mt-1">{runId}</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={handleDownload}
                  className="inline-flex items-center gap-3 rounded-2xl bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-4 text-white font-bold shadow-lg hover:from-blue-700 hover:to-blue-800 hover:shadow-xl transition-all duration-200 transform hover:scale-105"
                >
                  <IconDownload className="h-5 w-5"/>
                  Download DOCX
                </button>
                <button
                  onClick={handleDownloadLogs}
                  className="inline-flex items-center gap-3 rounded-2xl border-2 border-blue-200 bg-white px-6 py-4 text-blue-700 font-bold shadow-sm hover:border-blue-300 hover:shadow transition-all duration-200"
                >
                  <IconDownload className="h-5 w-5"/>
                  Download Logs
                </button>
              </div>
            </div>
          </section>
        )}
      </main>
      <Footer />
    </div>
  )
}
