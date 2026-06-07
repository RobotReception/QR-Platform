import { Loader2, Printer, AlertCircle, CheckCircle2, Download } from 'lucide-react'
import { Can, PERM } from '@shared/permissions'

interface GenerateButtonProps {
  handleGenerate: () => void
  isFormValid: boolean
  isPending: boolean
  totalInvitations: number
  localError: string | null
  isError: boolean
  error: any
  data: any
}

export function GenerateButton({
  handleGenerate,
  isFormValid,
  isPending,
  totalInvitations,
  localError,
  isError,
  error,
  data,
}: GenerateButtonProps) {
  return (
    <>
      <Can permission={PERM.INV_GENERATE}>
        <button
          onClick={handleGenerate}
          disabled={!isFormValid || isPending}
          className="inv-generate-btn"
        >
          {isPending ? (
            <>
              <Loader2 size={18} className="animate-spin" /> جاري توليد الدعوات...
            </>
          ) : (
            <>
              <Printer size={18} /> بدء التوليد ({totalInvitations} دعوة)
            </>
          )}
        </button>
      </Can>

      {/* Error */}
      {(localError || (isError && error)) && (
        <div className="inv-toast inv-toast--error">
          <AlertCircle size={16} /> {localError || (error as any)?.message}
        </div>
      )}

      {/* Success Result */}
      {data?.success && (
        <div className="inv-result">
          <div className="inv-result__info">
            <CheckCircle2 size={20} />
            <div>
              <strong>تم توليد الدعوات بنجاح!</strong>
              <span>
                {data.total_invitations} دعوة في {data.generation_time_ms}ms
              </span>
            </div>
          </div>
          <Can permission={PERM.BATCH_DOWNLOAD}>
            <div className="inv-result__actions">
              {data.pdf_url && (
                <a
                  href={data.pdf_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inv-dl-btn inv-dl-btn--pdf"
                >
                  <Download size={16} /> PDF ({data.pdf_size_mb?.toFixed(2)} MB)
                </a>
              )}
              {data.zip_url && (
                <a
                  href={data.zip_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inv-dl-btn inv-dl-btn--zip"
                >
                  <Download size={16} /> ZIP ({data.zip_size_mb?.toFixed(2)} MB)
                </a>
              )}
            </div>
          </Can>
        </div>
      )}
    </>
  )
}
