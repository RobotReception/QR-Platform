import { useDeferredValue, useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Shield,
  UserRoundCog,
  Users,
  Plus,
  Search,
  Trash2,
  UserX,
  Edit3,
  CheckSquare,
  Square,
  X,
  AlertCircle,
  Loader2,
  RefreshCcw,
  Crown,
  User,
} from 'lucide-react'
import { WorkspaceShell } from '@features/workspace/components/WorkspaceShell'
import { usersAPI } from '../api/usersApi'
import { useAuthStore } from '@features/auth/store/authStore'
import type { UserMember, UpdateMemberRequest } from '../types'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import '../pages/users.css'

// ═══════════════════════════════════════════════════════
// CONSTANTS
// ═══════════════════════════════════════════════════════
const roleLabel: Record<string, string> = {
  owner: 'مالك',
  admin: 'مدير',
  member: 'عضو',
  viewer: 'مشاهد',
}

const statusLabel: Record<string, string> = {
  active: 'نشط',
  invited: 'معلق',
  disabled: 'معطل',
}

const roleIcons: Record<string, typeof Crown> = {
  owner: Crown,
  admin: Shield,
  member: User,
  viewer: User,
}

const dateFmt = new Intl.DateTimeFormat('ar', { dateStyle: 'medium' })

function formatDate(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'غير متوفر' : dateFmt.format(date)
}

// ═══════════════════════════════════════════════════════
// DIALOG: Add Member
// ═══════════════════════════════════════════════════════
const createMemberSchema = z.object({
  full_name: z.string().min(2, 'الاسم يجب أن يكون حرفين على الأقل'),
  email: z.string().email('بريد إلكتروني غير صالح'),
  password: z.string().min(8, 'كلمة المرور يجب أن تكون 8 أحرف على الأقل'),
  role: z.enum(['admin', 'member', 'viewer']),
})

type CreateMemberForm = z.infer<typeof createMemberSchema>

function AddMemberDialog({
  isOpen,
  onClose,
  onSubmit,
  isLoading,
}: {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: CreateMemberForm) => void
  isLoading: boolean
}) {
  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors, isValid, isDirty },
  } = useForm<CreateMemberForm>({
    resolver: zodResolver(createMemberSchema),
    defaultValues: { role: 'member' },
    mode: 'onChange',
  })

  // Watch password for strength indicator
  const passwordValue = watch('password', '')
  const passwordRules = [
    { label: '8 أحرف على الأقل', test: (p: string) => p.length >= 8 },
    { label: 'حرف كبير (A-Z)', test: (p: string) => /[A-Z]/.test(p) },
    { label: 'رقم (0-9)', test: (p: string) => /[0-9]/.test(p) },
  ]

  // Reset form when dialog closes
  const handleClose = () => {
    reset()
    onClose()
  }

  const onFormSubmit = (data: CreateMemberForm) => {
    onSubmit(data)
    reset()
  }

  if (!isOpen) return null

  return (
    <div className="dialog-overlay" onClick={handleClose}>
      <motion.div
        className="dialog-content"
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="dialog-header">
          <h3>إضافة عضو جديد</h3>
          <button className="dialog-close" onClick={handleClose}><X size={18} /></button>
        </div>

        <form
          onSubmit={handleSubmit(onFormSubmit)}
          className="dialog-form"
          noValidate
        >
          <div className="form-field">
            <label>الاسم الكامل *</label>
            <input
              {...register('full_name')}
              placeholder="محمد العبدالله"
              className={errors.full_name ? 'error' : ''}
              disabled={isLoading}
            />
            {errors.full_name && (
              <span className="form-error">{errors.full_name.message}</span>
            )}
          </div>

          <div className="form-field">
            <label>البريد الإلكتروني *</label>
            <input
              {...register('email')}
              type="email"
              placeholder="user@company.com"
              dir="ltr"
              className={errors.email ? 'error' : ''}
              disabled={isLoading}
            />
            {errors.email && (
              <span className="form-error">{errors.email.message}</span>
            )}
          </div>

          <div className="form-field">
            <label>كلمة المرور *</label>
            <input
              {...register('password')}
              type="password"
              placeholder="••••••••"
              dir="ltr"
              className={errors.password ? 'error' : ''}
              disabled={isLoading}
            />
            {/* Password Strength Indicator */}
            {passwordValue && (
              <div className="password-strength">
                {passwordRules.map((rule) => (
                  <div
                    key={rule.label}
                    className={`strength-rule ${rule.test(passwordValue) ? 'valid' : ''}`}
                  >
                    <span className="rule-dot" />
                    <span className="rule-label">{rule.label}</span>
                  </div>
                ))}
              </div>
            )}
            {errors.password && (
              <span className="form-error">{errors.password.message}</span>
            )}
          </div>

          <div className="form-field">
            <label>الدور *</label>
            <select {...register('role')} className="form-select" disabled={isLoading}>
              <option value="admin">مدير (Admin)</option>
              <option value="member">عضو (Member)</option>
              <option value="viewer">مشاهد (Viewer)</option>
            </select>
          </div>

          <div className="dialog-actions">
            <button
              type="button"
              className="btn btn-ghost"
              onClick={handleClose}
              disabled={isLoading}
            >
              إلغاء
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isLoading || !isValid || !isDirty}
            >
              {isLoading ? (
                <><Loader2 size={16} className="spin" /> جاري الإضافة...</>
              ) : (
                <><Plus size={16} /> إضافة العضو</>
              )}
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════
// DIALOG: Edit Member
// ═══════════════════════════════════════════════════════
function EditMemberDialog({
  isOpen,
  onClose,
  member,
  onSubmit,
  isLoading,
}: {
  isOpen: boolean
  onClose: () => void
  member: UserMember | null
  onSubmit: (data: UpdateMemberRequest) => void
  isLoading: boolean
}) {
  const [role, setRole] = useState<UserMember['role']>(member?.role || 'member')
  const [status, setStatus] = useState<UserMember['status']>(member?.status || 'active')

  if (!isOpen || !member) return null

  return (
    <div className="dialog-overlay" onClick={onClose}>
      <motion.div
        className="dialog-content"
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="dialog-header">
          <h3>تعديل العضو</h3>
          <button className="dialog-close" onClick={onClose}><X size={18} /></button>
        </div>

        <div className="dialog-form">
          <div className="member-preview">
            <div className="member-avatar large">{(member.full_name || 'U').slice(0, 1)}</div>
            <div>
              <strong>{member.full_name || 'مستخدم بدون اسم'}</strong>
              <span>{member.user_id}</span>
            </div>
          </div>

          <div className="form-field">
            <label>الدور</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as UserMember['role'])}
              className="form-select"
              disabled={member.role === 'owner'}
            >
              <option value="admin">مدير (Admin)</option>
              <option value="member">عضو (Member)</option>
              <option value="viewer">مشاهد (Viewer)</option>
            </select>
            {member.role === 'owner' && (
              <span className="form-hint">لا يمكن تغيير دور المالك</span>
            )}
          </div>

          <div className="form-field">
            <label>الحالة</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value as UserMember['status'])}
              className="form-select"
              disabled={member.role === 'owner'}
            >
              <option value="active">نشط</option>
              <option value="disabled">معطل</option>
            </select>
            {member.role === 'owner' && (
              <span className="form-hint">لا يمكن تعطيل المالك</span>
            )}
          </div>

          <div className="dialog-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose}>إلغاء</button>
            <button
              type="button"
              className="btn btn-primary"
              disabled={isLoading || (role === member.role && status === member.status)}
              onClick={() => onSubmit({ role: role as UserMember['role'], status: status as UserMember['status'] })}
            >
              {isLoading ? <><Loader2 size={16} className="spin" /> جاري الحفظ...</> : <><Edit3 size={16} /> حفظ التغييرات</>}
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════
// DIALOG: Confirm Delete
// ═══════════════════════════════════════════════════════
function ConfirmDeleteDialog({
  isOpen,
  onClose,
  onConfirm,
  isLoading,
  title,
  message,
}: {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  isLoading: boolean
  title: string
  message: string
}) {
  if (!isOpen) return null

  return (
    <div className="dialog-overlay" onClick={onClose}>
      <motion.div
        className="dialog-content dialog-content--danger"
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="dialog-header dialog-header--danger">
          <div className="dialog-icon">
            <AlertCircle size={24} />
          </div>
          <h3>{title}</h3>
          <button className="dialog-close" onClick={onClose}><X size={18} /></button>
        </div>

        <p className="dialog-message">{message}</p>

        <div className="dialog-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>إلغاء</button>
          <button
            type="button"
            className="btn btn-danger"
            disabled={isLoading}
            onClick={onConfirm}
          >
            {isLoading ? <><Loader2 size={16} className="spin" /> جاري الحذف...</> : <><Trash2 size={16} /> تأكيد الحذف</>}
          </button>
        </div>
      </motion.div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════
export default function UsersPage() {
  const currentTenantId = useAuthStore(s => s.currentTenantId)
  const currentUserId = useAuthStore(s => s.user?.id)
  const currentTenant = useAuthStore(s => s.tenants.find(t => t.tenant_id === currentTenantId))
  const queryClient = useQueryClient()

  // ── State ──
  const [search, setSearch] = useState('')
  const [selectedUsers, setSelectedUsers] = useState<Set<string>>(new Set())
  const [showAddDialog, setShowAddDialog] = useState(false)
  const [editingMember, setEditingMember] = useState<UserMember | null>(null)
  const [deletingMember, setDeletingMember] = useState<UserMember | null>(null)
  const [showBulkDelete, setShowBulkDelete] = useState(false)
  const [roleFilter, setRoleFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')

  // ── Queries ──
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['users', currentTenantId],
    queryFn: usersAPI.list,
    enabled: Boolean(currentTenantId),
  })

  const members = data || []

  // ── Mutations ──
  const createMutation = useMutation({
    mutationFn: usersAPI.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users', currentTenantId] })
      queryClient.invalidateQueries({ queryKey: ['dashboard', currentTenantId] })
      setShowAddDialog(false)
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: string; body: UpdateMemberRequest }) =>
      usersAPI.update(id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users', currentTenantId] })
      queryClient.invalidateQueries({ queryKey: ['dashboard', currentTenantId] })
      setEditingMember(null)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: usersAPI.remove,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users', currentTenantId] })
      queryClient.invalidateQueries({ queryKey: ['dashboard', currentTenantId] })
      setDeletingMember(null)
      setShowBulkDelete(false)
      setSelectedUsers(new Set())
    },
  })

  const bulkDeleteMutation = useMutation({
    mutationFn: usersAPI.bulkRemove,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users', currentTenantId] })
      queryClient.invalidateQueries({ queryKey: ['dashboard', currentTenantId] })
      setShowBulkDelete(false)
      setSelectedUsers(new Set())
    },
  })

  // ── Filtering ──
  const deferredSearch = useDeferredValue(search)
  const normalizedSearch = deferredSearch.trim().toLowerCase()

  const filteredMembers = useMemo(() => {
    return members.filter((member) => {
      const matchesSearch = normalizedSearch
        ? (member.full_name || '').toLowerCase().includes(normalizedSearch) ||
          member.user_id.toLowerCase().includes(normalizedSearch) ||
          member.email?.toLowerCase().includes(normalizedSearch)
        : true

      const matchesRole = roleFilter === 'all' || member.role === roleFilter
      const matchesStatus = statusFilter === 'all' || member.status === statusFilter

      return matchesSearch && matchesRole && matchesStatus
    })
  }, [members, normalizedSearch, roleFilter, statusFilter])

  // ── Stats ──
  const stats = useMemo(() => ({
    total: members.length,
    active: members.filter(m => m.status === 'active').length,
    owners: members.filter(m => m.role === 'owner').length,
    admins: members.filter(m => m.role === 'admin').length,
    members: members.filter(m => m.role === 'member').length,
    viewers: members.filter(m => m.role === 'viewer').length,
    disabled: members.filter(m => m.status === 'disabled').length,
  }), [members])

  // ── Selection ──
  const toggleSelection = (userId: string) => {
    const newSelected = new Set(selectedUsers)
    if (newSelected.has(userId)) {
      newSelected.delete(userId)
    } else {
      newSelected.add(userId)
    }
    setSelectedUsers(newSelected)
  }

  const toggleAll = () => {
    if (selectedUsers.size === filteredMembers.length) {
      setSelectedUsers(new Set())
    } else {
      setSelectedUsers(new Set(filteredMembers.map(m => m.user_id)))
    }
  }

  const canDelete = (member: UserMember) => {
    return member.role !== 'owner' && member.user_id !== currentUserId
  }

  const canEdit = (member: UserMember) => {
    return member.role !== 'owner'
  }

  // ═══════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════
  return (
    <WorkspaceShell
      title="المستخدمون"
      subtitle={`${currentTenant?.name || 'مساحة العمل'} · إدارة أعضاء المؤسسة والصلاحيات الأساسية`}
      actions={
        <div className="header-actions">
          <button
            className="btn btn-primary"
            onClick={() => setShowAddDialog(true)}
          >
            <Plus size={16} /> إضافة عضو
          </button>
          <button className="dash-icon-btn" onClick={() => refetch()} aria-label="تحديث">
            <RefreshCcw size={18} />
          </button>
        </div>
      }
    >
      {/* ── Stats ── */}
      <section className="dash-stats-grid users-stats-grid">
        <div className="dash-stat">
          <div className="dash-stat__icon"><Users size={20} /></div>
          <div>
            <span className="dash-stat__label">إجمالي المستخدمين</span>
            <strong className="dash-stat__value">{stats.total}</strong>
            <span className="dash-stat__delta">{stats.active} نشط</span>
          </div>
        </div>
        <div className="dash-stat dash-stat--blue">
          <div className="dash-stat__icon"><Shield size={20} /></div>
          <div>
            <span className="dash-stat__label">الإدارة</span>
            <strong className="dash-stat__value">{stats.owners + stats.admins}</strong>
            <span className="dash-stat__delta">{stats.owners} مالك · {stats.admins} مدير</span>
          </div>
        </div>
        <div className="dash-stat dash-stat--gold">
          <div className="dash-stat__icon"><User size={20} /></div>
          <div>
            <span className="dash-stat__label">الأعضاء</span>
            <strong className="dash-stat__value">{stats.members}</strong>
            <span className="dash-stat__delta">{stats.viewers} مشاهد</span>
          </div>
        </div>
        <div className="dash-stat dash-stat--red">
          <div className="dash-stat__icon"><UserX size={20} /></div>
          <div>
            <span className="dash-stat__label">المعطّلون</span>
            <strong className="dash-stat__value">{stats.disabled}</strong>
            <span className="dash-stat__delta">يحتاجون تفعيل</span>
          </div>
        </div>
      </section>

      {/* ── Table ── */}
      <section className="dash-panel">
        <div className="dash-panel__head">
          <div>
            <span>أعضاء المؤسسة</span>
            <h2>إدارة الصلاحيات والحسابات</h2>
          </div>
          <UserRoundCog size={20} />
        </div>

        {/* Toolbar */}
        <div className="users-toolbar">
          <div className="toolbar-search">
            <Search size={16} className="search-icon" />
            <input
              className="users-search"
              placeholder="ابحث بالاسم، البريد، أو المعرّف..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <div className="toolbar-filters">
            <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)} className="filter-select">
              <option value="all">جميع الأدوار</option>
              <option value="owner">مالك</option>
              <option value="admin">مدير</option>
              <option value="member">عضو</option>
              <option value="viewer">مشاهد</option>
            </select>

            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="filter-select">
              <option value="all">جميع الحالات</option>
              <option value="active">نشط</option>
              <option value="disabled">معطل</option>
            </select>
          </div>
        </div>

        {/* Bulk Actions */}
        <AnimatePresence>
          {selectedUsers.size > 0 && (
            <motion.div
              className="bulk-actions-bar"
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
            >
              <span className="bulk-count">
                <CheckSquare size={16} /> {selectedUsers.size} محدد
              </span>
              <div className="bulk-buttons">
                <button
                  className="btn btn-ghost btn-sm"
                  onClick={() => setShowBulkDelete(true)}
                >
                  <Trash2 size={14} /> حذف المحدد
                </button>
                <button
                  className="btn btn-ghost btn-sm"
                  onClick={() => setSelectedUsers(new Set())}
                >
                  <X size={14} /> إلغاء التحديد
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Loading & Error */}
        {isLoading ? <div className="dash-empty">جار تحميل المستخدمين...</div> : null}
        {isError ? (
          <div className="dash-empty">
            <AlertCircle size={24} />
            <p>تعذر تحميل المستخدمين</p>
            <button className="btn btn-primary" onClick={() => refetch()}>إعادة المحاولة</button>
          </div>
        ) : null}

        {/* Table */}
        {!isLoading && !isError && (
          <div className="users-table-container">
            <div className="users-table">
              <div className="users-table__head">
                <span className="select-cell">
                  <button
                    className="checkbox-btn"
                    onClick={toggleAll}
                  >
                    {selectedUsers.size === filteredMembers.length && filteredMembers.length > 0
                      ? <CheckSquare size={18} />
                      : <Square size={18} />}
                  </button>
                </span>
                <span>المستخدم</span>
                <span>الدور</span>
                <span>الحالة</span>
                <span>تاريخ الانضمام</span>
                <span className="actions-cell">الإجراءات</span>
              </div>

              {filteredMembers.length ? (
                filteredMembers.map((member) => {
                  const RoleIcon = roleIcons[member.role] || User
                  const isSelected = selectedUsers.has(member.user_id)
                  const canEditMember = canEdit(member)
                  const canDeleteMember = canDelete(member)

                  return (
                    <motion.div
                      className={`users-row ${isSelected ? 'users-row--selected' : ''}`}
                      key={member.user_id}
                      layout
                    >
                      <span className="select-cell">
                        <button
                          className="checkbox-btn"
                          onClick={() => toggleSelection(member.user_id)}
                        >
                          {isSelected ? <CheckSquare size={18} /> : <Square size={18} />}
                        </button>
                      </span>

                      <div className="users-row__user">
                        <div className="member-avatar">{(member.full_name || 'U').slice(0, 1)}</div>
                        <div>
                          <strong>{member.full_name || 'مستخدم بدون اسم'}</strong>
                          <span>{member.user_id}</span>
                        </div>
                      </div>

                      <span className={`users-chip users-chip--${member.role}`}>
                        <RoleIcon size={14} />
                        {roleLabel[member.role] || member.role}
                      </span>

                      <span className={`users-status users-status--${member.status}`}>
                        {statusLabel[member.status] || member.status}
                      </span>

                      <span className="date-cell">{formatDate(member.created_at)}</span>

                      <span className="actions-cell">
                        <div className="row-actions">
                          {canEditMember && (
                            <button
                              className="action-btn"
                              onClick={() => setEditingMember(member)}
                              title="تعديل"
                            >
                              <Edit3 size={14} />
                            </button>
                          )}
                          {canDeleteMember && (
                            <button
                              className="action-btn action-btn--danger"
                              onClick={() => setDeletingMember(member)}
                              title="حذف"
                            >
                              <Trash2 size={14} />
                            </button>
                          )}
                        </div>
                      </span>
                    </motion.div>
                  )
                })
              ) : (
                <div className="dash-empty">
                  {normalizedSearch || roleFilter !== 'all' || statusFilter !== 'all'
                    ? 'لا توجد نتائج مطابقة للفلاتر المحددة'
                    : 'لا يوجد أعضاء في المؤسسة'}
                </div>
              )}
            </div>
          </div>
        )}
      </section>

      {/* ── Dialogs ── */}
      <AnimatePresence>
        {showAddDialog && (
          <AddMemberDialog
            isOpen={showAddDialog}
            onClose={() => setShowAddDialog(false)}
            onSubmit={(data) => createMutation.mutate(data)}
            isLoading={createMutation.isPending}
          />
        )}

        {editingMember && (
          <EditMemberDialog
            isOpen={!!editingMember}
            onClose={() => setEditingMember(null)}
            member={editingMember}
            onSubmit={(body) =>
              updateMutation.mutate({ id: editingMember.user_id, body })
            }
            isLoading={updateMutation.isPending}
          />
        )}

        {deletingMember && (
          <ConfirmDeleteDialog
            isOpen={!!deletingMember}
            onClose={() => setDeletingMember(null)}
            onConfirm={() => deleteMutation.mutate(deletingMember.user_id)}
            isLoading={deleteMutation.isPending}
            title="حذف العضو"
            message={`هل أنت متأكد من حذف "${deletingMember.full_name || deletingMember.user_id}"؟ لا يمكن التراجع عن هذا الإجراء.`}
          />
        )}

        {showBulkDelete && (
          <ConfirmDeleteDialog
            isOpen={showBulkDelete}
            onClose={() => setShowBulkDelete(false)}
            onConfirm={() => bulkDeleteMutation.mutate(Array.from(selectedUsers))}
            isLoading={bulkDeleteMutation.isPending}
            title="حذف متعدد"
            message={`هل أنت متأكد من حذف ${selectedUsers.size} عضو؟ لا يمكن التراجع عن هذا الإجراء.`}
          />
        )}
      </AnimatePresence>
    </WorkspaceShell>
  )
}
