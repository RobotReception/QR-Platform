/**
 * GuestsPage.tsx
 * Guest book management page with search, add, and edit.
 */
import { useState, useMemo } from 'react'
import { Users, Search, Plus, RefreshCw, Loader2 } from 'lucide-react'
import { WorkspaceShell } from '@features/workspace/components/WorkspaceShell'
import { useAuthStore } from '@features/auth/store/authStore'
import { useGuestsList, useDeleteGuest } from '../hooks/useGuests'
import { GuestCard } from '../components/GuestCard'
import { CreateGuestDialog } from '../components/CreateGuestDialog'
import type { Guest } from '../types'
import './guests.css'

export default function GuestsPage() {
  const tenantId = useAuthStore((s) => s.currentTenantId)
  const [search, setSearch] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [editGuest, setEditGuest] = useState<Guest | null>(null)
  const { data: guests, isLoading, isError, refetch } = useGuestsList()
  const deleteMutation = useDeleteGuest()

  const filtered = useMemo(() => {
    if (!guests) return []
    if (!search.trim()) return guests
    const q = search.toLowerCase()
    return guests.filter((g) =>
      g.full_name.toLowerCase().includes(q) ||
      g.full_name_ar?.includes(q) ||
      g.phone?.includes(q) ||
      g.email?.toLowerCase().includes(q) ||
      g.company?.toLowerCase().includes(q)
    )
  }, [guests, search])

  if (!tenantId) {
    return (
      <WorkspaceShell title="دفتر الضيوف" subtitle="">
        <div className="dash-state">
          <Users size={40} />
          <h1>لا توجد مساحة عمل محددة</h1>
          <p>اختر مساحة العمل من الحساب حتى تظهر بيانات الضيوف.</p>
        </div>
      </WorkspaceShell>
    )
  }

  return (
    <WorkspaceShell
      title="دفتر الضيوف"
      subtitle="إدارة قائمة الضيوف واستخدامها لإنشاء الدعوات"
      actions={
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          <Plus size={16} /> إضافة ضيف
        </button>
      }
    >
      {/* Toolbar */}
      <div className="inv-toolbar">
        <div className="inv-toolbar__search">
          <Search size={17} className="search-icon" />
          <input
            type="text"
            placeholder="بحث بالاسم أو الهاتف أو البريد..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        {guests && (
          <span className="guests-count">{filtered.length} ضيف</span>
        )}
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="inv-loading">
          <Loader2 size={32} className="animate-spin" />
          <span>جاري تحميل الضيوف...</span>
        </div>
      ) : isError ? (
        <div className="inv-empty">
          <Users size={36} />
          <h3>فشل تحميل الضيوف</h3>
          <button className="btn btn-ghost" onClick={() => refetch()}>
            <RefreshCw size={16} /> إعادة المحاولة
          </button>
        </div>
      ) : !filtered.length ? (
        <div className="inv-empty">
          <Users size={36} />
          <h3>{search ? 'لا توجد نتائج' : 'لا يوجد ضيوف بعد'}</h3>
          <p>{search ? 'حاول تعديل معايير البحث' : 'أضف ضيوفك لتتمكن من إنشاء دعوات جماعية بسهولة'}</p>
          {!search && (
            <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
              <Plus size={16} /> إضافة أول ضيف
            </button>
          )}
        </div>
      ) : (
        <div className="guests-list">
          {filtered.map((guest) => (
            <GuestCard
              key={guest.id}
              guest={guest}
              onEdit={(g) => setEditGuest(g)}
              onDelete={(id) => deleteMutation.mutate(id)}
            />
          ))}
        </div>
      )}

      {/* Dialogs */}
      {(showCreate || editGuest) && (
        <CreateGuestDialog
          isOpen
          onClose={() => { setShowCreate(false); setEditGuest(null) }}
          editGuest={editGuest}
        />
      )}
    </WorkspaceShell>
  )
}
