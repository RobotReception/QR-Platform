/**
 * TemplateSelectionModal.tsx
 * 🎯 Modal احترافي لاستخدام TemplateSelectionFlow
 */

import { ReactNode } from 'react'
import { X } from 'lucide-react'
import './template-selection-modal.css'

interface TemplateSelectionModalProps {
  isOpen: boolean
  children: ReactNode
  onClose: () => void
}

export function TemplateSelectionModal({ isOpen, children, onClose }: TemplateSelectionModalProps) {
  if (!isOpen) return null

  return (
    <div className="template-selection-modal-overlay" onClick={onClose}>
      <div className="template-selection-modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close-btn" onClick={onClose}>
          <X size={24} />
        </button>
        {children}
      </div>
    </div>
  )
}
