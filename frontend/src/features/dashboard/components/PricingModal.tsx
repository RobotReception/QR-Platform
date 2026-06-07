import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { X, Check, Loader2, Sparkles } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { subscriptionsAPI } from '../../settings/api/subscriptionsApi'
import './pricing.css'

interface PricingModalProps {
  isOpen: boolean
  onClose: () => void
  currentPlanCode?: string
}

const LIMIT_LABELS: Record<string, string> = {
  events_per_month: 'الفعاليات شهرياً',
  invitations_per_event: 'الدعوات لكل حدث',
  seats_max: 'المستخدمين في المنصة',
  storage_mb: 'مساحة التخزين',
}

function formatLimitValue(key: string, value: number) {
  if (value === -1) return 'غير محدود'
  if (key === 'storage_mb') {
    if (value >= 1000) return `${value / 1000} جيجابايت`
    return `${value} ميجابايت`
  }
  return value.toLocaleString('ar')
}

export function PricingModal({ isOpen, onClose, currentPlanCode = 'starter' }: PricingModalProps) {
  const [billingPeriod, setBillingPeriod] = useState<'monthly' | 'yearly'>('monthly')

  // Fetch plans from backend
  const { data: plans, isLoading, error } = useQuery({
    queryKey: ['pricing-plans'],
    queryFn: subscriptionsAPI.listPlans,
    enabled: isOpen,
  })

  // Checkout Session Mutation (PayPal)
  const checkoutMutation = useMutation({
    mutationFn: (planCode: string) => subscriptionsAPI.createCheckoutSession(planCode, 'paypal'),
    onSuccess: (data) => {
      if (data.checkout_url) {
        // Redirect to PayPal for approval
        window.location.href = data.checkout_url
      }
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || 'فشلت عملية التحضير للترقية. يرجى المحاولة لاحقاً.'
      alert(msg)
    },
  })

  if (!isOpen) return null

  // Helper to find sort order of current plan
  const sortedPlans = plans ? [...plans].sort((a, b) => a.sort_order - b.sort_order) : []
  const currentPlan = sortedPlans.find(p => p.code.toLowerCase() === currentPlanCode.toLowerCase())
  const currentSortOrder = currentPlan?.sort_order || 1

  return (
    <AnimatePresence>
      <motion.div
        className="pricing-overlay"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
      >
        <motion.div
          className="pricing-modal"
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          transition={{ type: 'spring', stiffness: 350, damping: 28 }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Close button */}
          <button className="pricing-modal__close" onClick={onClose} aria-label="إغلاق">
            <X size={20} />
          </button>

          {/* Header */}
          <div className="pricing-modal__header">
            <span className="dash-pill" style={{ color: '#c9a96e', background: 'rgba(201,169,110,0.08)' }}>
              <Sparkles size={14} className="spin" /> خطط الاشتراك ترقية الباقات
            </span>
            <h2 className="pricing-modal__title">اختر الخطة المناسبة لفعالياتك</h2>
            <p className="pricing-modal__subtitle">
              قم بترقية باقة اشتراكك للحصول على حدود أعلى، بوابات وصول إضافية، وقوالب مصممة مخصصة تلبي متطلبات تنظيم فعالياتك الاحترافية.
            </p>

            {/* Toggle Billing Period */}
            <div className="pricing-toggle-container">
              <button
                type="button"
                className={`pricing-toggle-btn ${billingPeriod === 'monthly' ? 'pricing-toggle-btn--active' : ''}`}
                onClick={() => setBillingPeriod('monthly')}
              >
                شهرياً
              </button>
              <button
                type="button"
                className={`pricing-toggle-btn ${billingPeriod === 'yearly' ? 'pricing-toggle-btn--active' : ''}`}
                onClick={() => setBillingPeriod('yearly')}
              >
                سنوياً
                <span className="pricing-toggle-discount">خصم 17%</span>
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="pricing-modal__content">
            {isLoading ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '300px', gap: '16px' }}>
                <Loader2 size={40} className="spin" style={{ color: '#c9a96e' }} />
                <span style={{ color: '#94a3b8', fontSize: '14px' }}>جاري تحميل خطط الاشتراك والأسعار…</span>
              </div>
            ) : error ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '300px', gap: '12px', textAlign: 'center' }}>
                <span style={{ color: '#f87171', fontSize: '15px', fontWeight: 600 }}>فشل تحميل خطط الاشتراك</span>
                <span style={{ color: '#64748b', fontSize: '13px' }}>يرجى التحقق من اتصالك بالإنترنت وإعادة المحاولة.</span>
              </div>
            ) : (
              <div className="pricing-grid">
                {sortedPlans.map((plan) => {
                  const isCurrent = plan.code.toLowerCase() === currentPlanCode.toLowerCase()
                  const isEnterprise = plan.code.toLowerCase() === 'enterprise'
                  const isPopular = plan.is_popular
                  
                  // Price based on toggle
                  const price = billingPeriod === 'monthly' ? plan.price_monthly : plan.price_yearly / 12
                  
                  // Determine button label and action
                  let btnLabel = 'ترقية الباقة'
                  let isDisabled = checkoutMutation.isPending
                  let btnVariant: 'primary' | 'secondary' = 'secondary'

                  if (isCurrent) {
                    btnLabel = 'الباقة الحالية'
                    isDisabled = true
                    btnVariant = 'secondary'
                  } else if (isEnterprise) {
                    btnLabel = 'تواصل معنا'
                    btnVariant = 'secondary'
                  } else if (plan.sort_order < currentSortOrder) {
                    btnLabel = 'تغيير الباقة'
                    btnVariant = 'secondary'
                  } else {
                    btnLabel = 'ترقية الآن'
                    btnVariant = 'primary'
                  }

                  // Find limits we care about
                  const eventLimit = plan.limits.find(l => l.key === 'events_per_month')?.value ?? 0
                  const invitationLimit = plan.limits.find(l => l.key === 'invitations_per_event')?.value ?? 0
                  const seatsLimit = plan.limits.find(l => l.key === 'seats_max')?.value ?? 0
                  const storageLimit = plan.limits.find(l => l.key === 'storage_mb')?.value ?? 0

                  return (
                    <div
                      key={plan.id}
                      className={`plan-card ${isPopular ? 'plan-card--popular' : ''}`}
                    >
                      {isPopular && <div className="plan-popular-badge">الأكثر شعبية</div>}

                      {/* Header */}
                      <div className="plan-card__header">
                        <h3 className="plan-card__name">{plan.name}</h3>
                        <p className="plan-card__desc">{plan.description}</p>
                      </div>

                      {/* Pricing */}
                      <div className="plan-card__pricing">
                        {isEnterprise ? (
                          <span className="plan-card__price-label">تسعير خاص</span>
                        ) : (
                          <>
                            <span className="plan-card__price-amount">{price === 0 ? '0' : price.toLocaleString('en-US', { maximumFractionDigits: 0 })}</span>
                            <span className="plan-card__price-period">ر.س / شهر</span>
                          </>
                        )}
                      </div>

                      {/* Limits Summary */}
                      <div className="plan-limits-summary">
                        <div className="limit-item">
                          <span>{LIMIT_LABELS.events_per_month}</span>
                          <strong className={eventLimit === -1 ? 'ar' : ''}>
                            {formatLimitValue('events_per_month', eventLimit)}
                          </strong>
                        </div>
                        <div className="limit-item">
                          <span>{LIMIT_LABELS.invitations_per_event}</span>
                          <strong className={invitationLimit === -1 ? 'ar' : ''}>
                            {formatLimitValue('invitations_per_event', invitationLimit)}
                          </strong>
                        </div>
                        <div className="limit-item">
                          <span>{LIMIT_LABELS.seats_max}</span>
                          <strong className={seatsLimit === -1 ? 'ar' : ''}>
                            {formatLimitValue('seats_max', seatsLimit)}
                          </strong>
                        </div>
                        <div className="limit-item">
                          <span>{LIMIT_LABELS.storage_mb}</span>
                          <strong className={storageLimit === -1 ? 'ar' : ''}>
                            {formatLimitValue('storage_mb', storageLimit)}
                          </strong>
                        </div>
                      </div>

                      {/* Features */}
                      <div className="plan-features-list">
                        {(plan.features || []).slice(0, 7).map((feat, idx) => (
                          <div key={idx} className="feature-check-item">
                            <Check size={14} />
                            <span>{feat}</span>
                          </div>
                        ))}
                      </div>

                      {/* Action Button */}
                      <button
                        type="button"
                        className={`plan-card__btn plan-card__btn--${btnVariant}`}
                        disabled={isDisabled}
                        onClick={() => {
                          if (isEnterprise) {
                            window.location.href = 'mailto:sales@qentry.com?subject=طلب ترقية لباقة Enterprise'
                          } else {
                            checkoutMutation.mutate(plan.code)
                          }
                        }}
                      >
                        {checkoutMutation.isPending && checkoutMutation.variables === plan.code ? (
                          <>
                            <Loader2 size={16} className="spin" />
                            جاري التوجيه…
                          </>
                        ) : (
                          <>
                            {isCurrent ? null : <Sparkles size={14} />}
                            {btnLabel}
                          </>
                        )}
                      </button>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
