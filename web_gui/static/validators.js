/**
 * 顶点验证器模块
 * 提供对顶点输入格式的完整验证功能
 */

const VertexValidator = {
    /**
     * 检测中文符号（冒号、逗号、分号、空格）
     * @param {string} vertexString - 顶点字符串
     * @returns {string|null} 错误信息或 null
     */
    detectChineseSymbols(vertexString) {
        const chineseChecks = [
            {
                char: '：',
                english: ':',
                message: '顶点分隔符格式错误，检测到中文冒号 `：`，请改用英文冒号 `:` 分隔顶点'
            },
            {
                char: '，',
                english: ',',
                message: '坐标分隔符格式错误，检测到中文逗号 `，`，请改用英文逗号 `,` 分隔坐标'
            },
            {
                char: '；',
                english: ':',
                message: '顶点分隔符格式错误，检测到中文分号 `；`，应使用英文冒号 `:`'
            },
            {
                char: '\u3000',
                english: ' ',
                message: '空格格式错误，检测到中文空格，请改用英文空格'
            }
        ];

        for (const check of chineseChecks) {
            if (vertexString.includes(check.char)) {
                return check.message;
            }
        }

        return null;
    },

    /**
     * 检测无效的分隔符（分号、斜杠等）
     * @param {string} vertexString - 顶点字符串
     * @returns {string|null} 错误信息或 null
     */
    detectInvalidSeparators(vertexString) {
        // 分号作为主要分隔符（冒号已是合法分隔符，分号不是）
        if (vertexString.includes(';')) {
            return '顶点分隔符格式错误，检测到分号 `;`，应使用英文冒号 `:` 分隔顶点';
        }

        // 斜杠（可能用作分隔符）
        if (vertexString.includes('/')) {
            return '坐标分隔符格式错误，检测到斜杠 `/`，应使用英文逗号 `,` 分隔坐标，用英文冒号 `:` 分隔顶点';
        }

        // 管道符
        if (vertexString.includes('|')) {
            return '顶点分隔符格式错误，检测到管道符 `|`，应使用英文冒号 `:` 分隔顶点';
        }

        // 波浪线
        if (vertexString.includes('~')) {
            return '顶点格式错误，检测到波浪线 `~`，应使用英文冒号 `:` 分隔顶点';
        }

        return null;
    },

    /**
     * 获取详细的符号错误信息
     * @param {string} vertexString - 顶点字符串
     * @returns {string|null} 错误信息或 null
     */
    getDetailedSymbolError(vertexString) {
        // 优先检查中文符号
        const chineseError = this.detectChineseSymbols(vertexString);
        if (chineseError) {
            return chineseError;
        }

        // 检查其他无效分隔符
        const separatorError = this.detectInvalidSeparators(vertexString);
        if (separatorError) {
            return separatorError;
        }

        return null;
    },

    /**
     * 验证顶点字符串格式是否符合 x1,y1:x2,y2:...
     * @param {string} vertexString - 顶点字符串
     * @returns {boolean} 格式是否正确
     */
    validateVertexFormat(vertexString) {
        if (!vertexString || typeof vertexString !== 'string') {
            return false;
        }

        // 删除前后空白
        const trimmed = vertexString.trim();

        // 检查是否为空
        if (trimmed.length === 0) {
            return false;
        }

        // 检查基本格式：冒号分隔，每个坐标由逗号分隔的两个数字组成
        const vertexPattern = /^[\d.,:\s+-]+$/;
        if (!vertexPattern.test(trimmed)) {
            return false;
        }

        // 检查冒号和逗号的基本结构
        const vertices = trimmed.split(':');
        if (vertices.length < 3) {
            return false; // 至少需要3个顶点
        }

        // 检查每个顶点是否恰好有一个逗号分隔
        for (const vertex of vertices) {
            const parts = vertex.trim().split(',');
            if (parts.length !== 2) {
                return false;
            }
        }

        return true;
    },

    /**
     * 解析顶点字符串为坐标数组
     * @param {string} vertexString - 顶点字符串
     * @returns {Array<Array<number>>|null} 解析后的坐标数组 [[x1,y1], [x2,y2], ...] 或 null
     */
    parseVertices(vertexString) {
        if (!vertexString || typeof vertexString !== 'string') {
            return null;
        }

        try {
            const trimmed = vertexString.trim();
            const vertexArray = [];

            const vertices = trimmed.split(':');

            for (const vertex of vertices) {
                const parts = vertex.trim().split(',');
                if (parts.length !== 2) {
                    return null;
                }

                const x = parseFloat(parts[0].trim());
                const y = parseFloat(parts[1].trim());

                if (isNaN(x) || isNaN(y)) {
                    return null;
                }

                vertexArray.push([x, y]);
            }

            return vertexArray.length > 0 ? vertexArray : null;
        } catch (e) {
            return null;
        }
    },

    /**
     * 检查顶点数量是否满足最小要求
     * @param {Array<Array<number>>} vertices - 坐标数组
     * @returns {boolean} 顶点数量是否有效
     */
    validateVertexCount(vertices) {
        return Array.isArray(vertices) && vertices.length >= 3;
    },

    /**
     * 检查所有坐标是否为有效的数字
     * @param {Array<Array<number>>} vertices - 坐标数组
     * @returns {boolean} 所有坐标是否有效
     */
    validateCoordinateValues(vertices) {
        if (!Array.isArray(vertices)) {
            return false;
        }

        for (const vertex of vertices) {
            if (!Array.isArray(vertex) || vertex.length !== 2) {
                return false;
            }

            const [x, y] = vertex;
            if (typeof x !== 'number' || typeof y !== 'number' || isNaN(x) || isNaN(y)) {
                return false;
            }
        }

        return true;
    },

    /**
     * 检查是否存在重复的顶点
     * @param {Array<Array<number>>} vertices - 坐标数组
     * @returns {Object} {hasDuplicates: boolean, duplicateInfo: Array}
     */
    validateNoDuplicates(vertices) {
        if (!Array.isArray(vertices) || vertices.length === 0) {
            return { hasDuplicates: false, duplicateInfo: [] };
        }

        const duplicateInfo = [];
        const seenVertices = new Map();

        for (let i = 0; i < vertices.length; i++) {
            const [x, y] = vertices[i];
            // 使用字符串作为键来比较坐标
            const key = `${x},${y}`;

            if (seenVertices.has(key)) {
                duplicateInfo.push({
                    index: i,
                    firstIndex: seenVertices.get(key),
                    x: x,
                    y: y
                });
            } else {
                seenVertices.set(key, i);
            }
        }

        return {
            hasDuplicates: duplicateInfo.length > 0,
            duplicateInfo: duplicateInfo
        };
    },

    /**
     * 综合验证函数 - 进行完整的顶点验证
     * @param {string} vertexString - 顶点字符串
     * @returns {Object} {valid: boolean, errors: [string], vertices: Array|null, vertexCount: number}
     */
    validateVertices(vertexString) {
        const result = {
            valid: true,
            errors: [],
            vertices: null,
            vertexCount: 0
        };

        // 检查输入是否为空
        if (!vertexString || typeof vertexString !== 'string') {
            result.valid = false;
            result.errors.push('顶点输入不能为空');
            return result;
        }

        const trimmed = vertexString.trim();
        if (trimmed.length === 0) {
            result.valid = false;
            result.errors.push('顶点输入不能为空');
            return result;
        }

        // 检查符号错误（优先检查，比格式检查更具体）
        const symbolError = this.getDetailedSymbolError(vertexString);
        if (symbolError) {
            result.valid = false;
            result.errors.push(symbolError);
            return result;
        }

        // 检查格式
        if (!this.validateVertexFormat(vertexString)) {
            result.valid = false;
            result.errors.push('顶点格式错误，应为 "x1,y1:x2,y2:x3,y3"，例如 "0,0:10,0:10,10"');
            return result;
        }

        // 解析顶点
        const vertices = this.parseVertices(vertexString);
        if (vertices === null) {
            result.valid = false;
            result.errors.push('顶点解析失败，请检查坐标是否为有效的数字');
            return result;
        }

        result.vertices = vertices;
        result.vertexCount = vertices.length;

        // 检查顶点数量
        if (!this.validateVertexCount(vertices)) {
            result.valid = false;
            result.errors.push(`顶点数量不足，至少需要3个顶点，当前有 ${vertices.length} 个`);
            return result;
        }

        // 检查坐标有效性
        if (!this.validateCoordinateValues(vertices)) {
            result.valid = false;
            result.errors.push('存在无效的坐标值');
            return result;
        }

        // 检查重复顶点
        const duplicateCheck = this.validateNoDuplicates(vertices);
        if (duplicateCheck.hasDuplicates) {
            const dupInfo = duplicateCheck.duplicateInfo;
            const dupMessages = dupInfo.map(dup =>
                `第 ${dup.index + 1} 个顶点 (${dup.x},${dup.y}) 与第 ${dup.firstIndex + 1} 个顶点重复`
            );
            result.valid = false;
            result.errors.push('存在重复的顶点坐标：');
            result.errors = result.errors.concat(dupMessages);
            return result;
        }

        // 所有检查都通过
        result.valid = true;
        result.errors = [];

        return result;
    }
};

// 导出供其他模块使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VertexValidator;
}
