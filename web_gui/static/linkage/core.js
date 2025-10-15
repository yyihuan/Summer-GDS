// 形状联动核心工具库
window.LinkageCore = {
    version: '1.0.0',
    debug: true,

    // 可继承属性路径配置
    INHERITABLE_PROPERTIES: [
        'vertices',
        'fillet.type',
        'fillet.radius',
        'fillet.radii',
        'fillet.precision',
        'fillet.convex_radius',
        'fillet.concave_radius',
        'zoom',
        '_metadata',
        'ring_width',
        'ring_space',
        'ring_num'
    ],

    // 属性路径工具
    getNestedProperty(obj, path) {
        if (!obj || !path) return undefined;
        return path.split('.').reduce((current, key) => current?.[key], obj);
    },

    setNestedProperty(obj, path, value) {
        if (!obj || !path) return;
        const keys = path.split('.');
        const lastKey = keys.pop();
        const target = keys.reduce((current, key) => {
            if (!current[key]) current[key] = {};
            return current[key];
        }, obj);
        target[lastKey] = value;
    },

    // 深度比较
    deepEqual(a, b) {
        if (a === b) return true;
        if (a == null || b == null) return false;
        if (typeof a !== 'object' || typeof b !== 'object') return false;

        const keysA = Object.keys(a);
        const keysB = Object.keys(b);
        if (keysA.length !== keysB.length) return false;

        return keysA.every(key => this.deepEqual(a[key], b[key]));
    },

    // 日志工具
    log(level, message, data = null) {
        if (!this.debug) return;
        const timestamp = new Date().toISOString().substr(11, 12);
        console[level](`[Linkage ${timestamp}] ${message}`, data || '');
    }
};
