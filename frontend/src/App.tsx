import { useState } from 'react'

function App() {
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0])
      setError(null)
    }
  }

  const handleUpload = async () => {
    if (!file) return

    setLoading(true)
    setError(null)
    
    // Bereitet die Datei für den HTTP-Transfer vor
    const formData = new FormData()
    formData.append('file', file)

    try {
      // Sendet den POST-Request an euer lokales FastAPI Backend
      const response = await fetch('http://localhost:8000/api/v1/parse-cv', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Ein Fehler ist aufgetreten')
      }

      const data = await response.json()
      setResult(data) // Speichert das Pydantic-JSON im State
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
      <h1>Career Compass - CV Parser</h1>
      
      <div style={{ marginBottom: '1rem' }}>
        <input type="file" accept=".pdf" onChange={handleFileChange} />
        <button onClick={handleUpload} disabled={!file || loading} style={{ marginLeft: '1rem' }}>
          {loading ? 'Analysiere PDF...' : 'Lebenslauf hochladen'}
        </button>
      </div>

      {error && <div style={{ color: 'red', marginBottom: '1rem' }}>Fehler: {error}</div>}

      {result && (
        <div style={{ marginTop: '2rem' }}>
          <h2>Extrahiertes Profil:</h2>
          <pre style={{ background: '#f4f4f4', padding: '1rem', borderRadius: '4px', overflowX: 'auto' }}>
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}

export default App