
@subscription_bp.route('/create-coupon', methods=['POST'])
@token_required
def create_coupon():
    """Create a coupon for testing/admin use. In production restrict this to admins only."""
    data = request.get_json(silent=True) or {}
    code = (data.get('code') or '').strip()
    try:
        discount = int(data.get('discount_percent', 0))
    except Exception:
        return jsonify({'error': 'Invalid discount_percent'}), 400
    if not code or discount <= 0 or discount > 100:
        return jsonify({'error': 'Invalid coupon parameters'}), 400
    expires_in_days = data.get('expires_in_days')
    max_uses = data.get('max_uses')
    from datetime import timedelta
    expires_at = None
    if isinstance(expires_in_days, (int, float)) and expires_in_days > 0:
        expires_at = utc_now() + timedelta(days=int(expires_in_days))
    try:
        coupon = subscription_service.create_coupon(code, discount, expires_at=expires_at, max_uses=max_uses)
        return jsonify({'coupon': coupon}), 201
    except Exception as e:
        current_app.logger.exception('Failed to create coupon')
        return jsonify({'error': str(e)}), 500

