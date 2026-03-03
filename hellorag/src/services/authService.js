/**
 * 星火知识库API鉴权服务
 * 严格按照ApiAuthUtil.java实现的认证逻辑
 */
// 移除Node.js特有的require语句，改为纯浏览器环境实现

class AuthService {
  constructor(appId, secret) {
    this.appId = appId;
    this.secret = secret;
    this.pythonScriptPath = '/d:/WorkSpace/03 VueWorkSpace/hellorag/Document_upload.py';
    // 与Java代码完全一致的MD5字符表
    this.MD5_TABLE = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f'];
    // 调试日志
    console.log('===== AuthService 初始化 =====');
    console.log('appId:', this.appId);
    console.log('secret:', this.secret ? '已设置' : '未设置');
    console.log('Python脚本路径:', this.pythonScriptPath);
    console.log('============================');
  }

  // 由于浏览器环境限制，不再使用Python脚本，直接使用JavaScript实现鉴权
  getAuthInfo() {
    console.log('===== 开始生成鉴权信息 =====');
    return new Promise((resolve, reject) => {
      try {
        // 生成秒级时间戳，与Java保持一致
        const timestamp = Math.floor(Date.now() / 1000).toString();
        console.log('生成的timestamp:', timestamp);
        
        const signature = this.getSignatureByBackup(timestamp);
        
        const authInfo = {
          appId: this.appId,
          timestamp: timestamp,
          signature
        };
        
        console.log('生成的鉴权信息:', authInfo);
        console.log('===== 鉴权信息生成完成 =====');
        resolve(authInfo);
      } catch (error) {
        console.error('生成鉴权信息失败:', error);
        reject(error);
      }
    });
  }
  
  // 备份的签名生成方法（仅在Python脚本失败时使用）
  getSignatureByBackup(timestamp) {
    console.log('使用备份方案生成签名');
    const combined = this.appId + timestamp;
    const md5Result = this.md5(combined);
    return this.hmacSHA1Encrypt(md5Result, this.secret);
  }

    // 注意：原始的getSignature方法已被getAuthInfo取代，不再直接提供此方法

  /**
   * MD5加密函数 - 纯JavaScript实现，严格按照ApiAuthUtil.java
   * @param {string} content - 要加密的内容
   * @returns {string} - 返回MD5加密后的十六进制字符串
   */
  md5(content) {
    try {
      console.log('===== 开始MD5加密 =====');
      console.log('加密内容:', content);
      
      // 纯JavaScript实现的MD5算法，确保与Java结果一致
      const md5Table = this.MD5_TABLE;
      
      // 将字符串转换为UTF-8编码的字节数组
      function stringToUtf8Bytes(str) {
        const bytes = [];
        for (let i = 0; i < str.length; i++) {
          let charCode = str.charCodeAt(i);
          if (charCode < 0x80) {
            bytes.push(charCode);
          } else if (charCode < 0x800) {
            bytes.push(0xc0 | (charCode >> 6));
            bytes.push(0x80 | (charCode & 0x3f));
          } else if (charCode < 0xd800 || charCode >= 0xe000) {
            bytes.push(0xe0 | (charCode >> 12));
            bytes.push(0x80 | ((charCode >> 6) & 0x3f));
            bytes.push(0x80 | (charCode & 0x3f));
          } else {
            // 处理代理对
            i++;
            const lowChar = str.charCodeAt(i);
            const combined = ((charCode & 0x3ff) << 10) | (lowChar & 0x3ff);
            const codePoint = combined + 0x10000;
            bytes.push(0xf0 | (codePoint >> 18));
            bytes.push(0x80 | ((codePoint >> 12) & 0x3f));
            bytes.push(0x80 | ((codePoint >> 6) & 0x3f));
            bytes.push(0x80 | (codePoint & 0x3f));
          }
        }
        return bytes;
      }

      const data = stringToUtf8Bytes(content);
      
      // MD5算法常量
      let h0 = 0x67452301;
      let h1 = 0xefcdab89;
      let h2 = 0x98badcfe;
      let h3 = 0x10325476;
      
      // 填充数据
      const originalLength = data.length * 8;
      const paddingLength = (originalLength % 512 < 448) ? 
                            (448 - originalLength % 512) : 
                            (512 + 448 - originalLength % 512);
      
      // 计算需要添加的字节数
      const padBytes = Math.ceil(paddingLength / 8);
      const paddedData = [...data];
      
      // 添加填充位
      paddedData.push(0x80); // 10000000
      for (let i = 1; i < padBytes; i++) {
        paddedData.push(0x00);
      }
      
      // 添加原始长度（64位，小端序）
      paddedData.push((originalLength >>> 0) & 0xff);
      paddedData.push((originalLength >>> 8) & 0xff);
      paddedData.push((originalLength >>> 16) & 0xff);
      paddedData.push((originalLength >>> 24) & 0xff);
      paddedData.push(0);
      paddedData.push(0);
      paddedData.push(0);
      paddedData.push(0);
      
      // 处理每个512位块
      for (let i = 0; i < paddedData.length; i += 64) {
        const w = new Array(16);
        for (let j = 0; j < 16; j++) {
          w[j] = paddedData[i + j * 4] << 24 | 
                 paddedData[i + j * 4 + 1] << 16 | 
                 paddedData[i + j * 4 + 2] << 8 | 
                 paddedData[i + j * 4 + 3];
        }
        
        let a = h0;
        let b = h1;
        let c = h2;
        let d = h3;
        
        // 四轮操作
        // 第一轮
        a = this._ff(a, b, c, d, w[0], 7, 0xd76aa478);
        d = this._ff(d, a, b, c, w[1], 12, 0xe8c7b756);
        c = this._ff(c, d, a, b, w[2], 17, 0x242070db);
        b = this._ff(b, c, d, a, w[3], 22, 0xc1bdceee);
        a = this._ff(a, b, c, d, w[4], 7, 0xf57c0faf);
        d = this._ff(d, a, b, c, w[5], 12, 0x4787c62a);
        c = this._ff(c, d, a, b, w[6], 17, 0xa8304613);
        b = this._ff(b, c, d, a, w[7], 22, 0xfd469501);
        a = this._ff(a, b, c, d, w[8], 7, 0x698098d8);
        d = this._ff(d, a, b, c, w[9], 12, 0x8b44f7af);
        c = this._ff(c, d, a, b, w[10], 17, 0xffff5bb1);
        b = this._ff(b, c, d, a, w[11], 22, 0x895cd7be);
        a = this._ff(a, b, c, d, w[12], 7, 0x6b901122);
        d = this._ff(d, a, b, c, w[13], 12, 0xfd987193);
        c = this._ff(c, d, a, b, w[14], 17, 0xa679438e);
        b = this._ff(b, c, d, a, w[15], 22, 0x49b40821);
        
        // 第二轮
        a = this._gg(a, b, c, d, w[1], 5, 0xf61e2562);
        d = this._gg(d, a, b, c, w[6], 9, 0xc040b340);
        c = this._gg(c, d, a, b, w[11], 14, 0x265e5a51);
        b = this._gg(b, c, d, a, w[0], 20, 0xe9b6c7aa);
        a = this._gg(a, b, c, d, w[5], 5, 0xd62f105d);
        d = this._gg(d, a, b, c, w[10], 9, 0x02441453);
        c = this._gg(c, d, a, b, w[15], 14, 0xd8a1e681);
        b = this._gg(b, c, d, a, w[4], 20, 0xe7d3fbc8);
        a = this._gg(a, b, c, d, w[9], 5, 0x21e1cde6);
        d = this._gg(d, a, b, c, w[14], 9, 0xc33707d6);
        c = this._gg(c, d, a, b, w[3], 14, 0xf4d50d87);
        b = this._gg(b, c, d, a, w[8], 20, 0x455a14ed);
        a = this._gg(a, b, c, d, w[13], 5, 0xa9e3e905);
        d = this._gg(d, a, b, c, w[2], 9, 0xfcefa3f8);
        c = this._gg(c, d, a, b, w[7], 14, 0x676f02d9);
        b = this._gg(b, c, d, a, w[12], 20, 0x8d2a4c8a);
        
        // 第三轮
        a = this._hh(a, b, c, d, w[5], 4, 0xfffa3942);
        d = this._hh(d, a, b, c, w[8], 11, 0x8771f681);
        c = this._hh(c, d, a, b, w[11], 16, 0x6d9d6122);
        b = this._hh(b, c, d, a, w[14], 23, 0xfde5380c);
        a = this._hh(a, b, c, d, w[1], 4, 0xa4beea44);
        d = this._hh(d, a, b, c, w[4], 11, 0x4bdecfa9);
        c = this._hh(c, d, a, b, w[7], 16, 0xf6bb4b60);
        b = this._hh(b, c, d, a, w[10], 23, 0xbebfbc70);
        a = this._hh(a, b, c, d, w[13], 4, 0x289b7ec6);
        d = this._hh(d, a, b, c, w[0], 11, 0xeaa127fa);
        c = this._hh(c, d, a, b, w[3], 16, 0xd4ef3085);
        b = this._hh(b, c, d, a, w[6], 23, 0x04881d05);
        a = this._hh(a, b, c, d, w[9], 4, 0xd9d4d039);
        d = this._hh(d, a, b, c, w[12], 11, 0xe6db99e5);
        c = this._hh(c, d, a, b, w[15], 16, 0x1fa27cf8);
        b = this._hh(b, c, d, a, w[2], 23, 0xc4ac5665);
        
        // 第四轮
        a = this._ii(a, b, c, d, w[0], 6, 0xf4292244);
        d = this._ii(d, a, b, c, w[7], 10, 0x432aff97);
        c = this._ii(c, d, a, b, w[14], 15, 0xab9423a7);
        b = this._ii(b, c, d, a, w[5], 21, 0xfc93a039);
        a = this._ii(a, b, c, d, w[12], 6, 0x655b59c3);
        d = this._ii(d, a, b, c, w[3], 10, 0x8f0ccc92);
        c = this._ii(c, d, a, b, w[10], 15, 0xffeff47d);
        b = this._ii(b, c, d, a, w[1], 21, 0x85845dd1);
        a = this._ii(a, b, c, d, w[8], 6, 0x6fa87e4f);
        d = this._ii(d, a, b, c, w[15], 10, 0xfe2ce6e0);
        c = this._ii(c, d, a, b, w[6], 15, 0xa3014314);
        b = this._ii(b, c, d, a, w[13], 21, 0x4e0811a1);
        a = this._ii(a, b, c, d, w[4], 6, 0xf7537e82);
        d = this._ii(d, a, b, c, w[11], 10, 0xbd3af235);
        c = this._ii(c, d, a, b, w[2], 15, 0x2ad7d2bb);
        b = this._ii(b, c, d, a, w[9], 21, 0xeb86d391);
        
        // 更新哈希值
        h0 = this._add32(h0, a);
        h1 = this._add32(h1, b);
        h2 = this._add32(h2, c);
        h3 = this._add32(h3, d);
      }
      
      // 将哈希值转换为十六进制字符串
      const hex = [];
      const words = [h0, h1, h2, h3];
      console.log('MD5哈希值:', { h0, h1, h2, h3 });
      
      for (let i = 0; i < words.length; i++) {
        for (let j = 0; j < 4; j++) {
          hex.push(md5Table[(words[i] >> (j * 8 + 4)) & 0x0f]);
          hex.push(md5Table[(words[i] >> (j * 8)) & 0x0f]);
        }
      }
      
      const md5Result = hex.join('');
      console.log('MD5加密结果:', md5Result);
      console.log('===== MD5加密完成 =====');
      
      return md5Result;
    } catch (error) {
      console.error('MD5加密失败:', error);
      throw error;
    }
  }

  // MD5辅助函数
  _ff(a, b, c, d, x, s, t) {
    const temp = this._add32(this._add32(this._add32(a, ((b & c) | (~b & d))), x), t);
    return (temp << s) | (temp >>> (32 - s));
  }

  _gg(a, b, c, d, x, s, t) {
    const temp = this._add32(this._add32(this._add32(a, ((b & d) | (c & ~d))), x), t);
    return (temp << s) | (temp >>> (32 - s));
  }

  _hh(a, b, c, d, x, s, t) {
    const temp = this._add32(this._add32(this._add32(a, (b ^ c ^ d)), x), t);
    return (temp << s) | (temp >>> (32 - s));
  }

  _ii(a, b, c, d, x, s, t) {
    const temp = this._add32(this._add32(this._add32(a, (c ^ (b | ~d))), x), t);
    return (temp << s) | (temp >>> (32 - s));
  }

  _add32(x, y) {
    const lsw = (x & 0xffff) + (y & 0xffff);
    const msw = (x >>> 16) + (y >>> 16) + (lsw >>> 16);
    return ((msw << 16) | (lsw & 0xffff)) >>> 0;
  }

  /**
   * HmacSHA1加密实现 - 严格按照Java ApiAuthUtil.hmacSHA1Encrypt方法实现
   * @param {string} encryptText - 要加密的文本（对应Java中的auth）
   * @param {string} encryptKey - 加密密钥（对应Java中的secret）
   * @returns {string} Base64编码的HMAC-SHA1结果
   */
  hmacSHA1Encrypt(encryptText, encryptKey) {
    try {
      console.log('===== 开始HMAC-SHA1加密 =====');
      console.log('encryptText:', encryptText);
      console.log('encryptKey:', encryptKey);
      // 纯JavaScript实现的HMAC-SHA1算法
      const blockSize = 64;
      
      // 将字符串转换为UTF-8字节数组
      function stringToUtf8Bytes(str) {
        const bytes = [];
        for (let i = 0; i < str.length; i++) {
          let charCode = str.charCodeAt(i);
          if (charCode < 0x80) {
            bytes.push(charCode);
          } else if (charCode < 0x800) {
            bytes.push(0xc0 | (charCode >> 6));
            bytes.push(0x80 | (charCode & 0x3f));
          } else if (charCode < 0xd800 || charCode >= 0xe000) {
            bytes.push(0xe0 | (charCode >> 12));
            bytes.push(0x80 | ((charCode >> 6) & 0x3f));
            bytes.push(0x80 | (charCode & 0x3f));
          } else {
            // 处理代理对
            i++;
            const lowChar = str.charCodeAt(i);
            const combined = ((charCode & 0x3ff) << 10) | (lowChar & 0x3ff);
            const codePoint = combined + 0x10000;
            bytes.push(0xf0 | (codePoint >> 18));
            bytes.push(0x80 | ((codePoint >> 12) & 0x3f));
            bytes.push(0x80 | ((codePoint >> 6) & 0x3f));
            bytes.push(0x80 | (codePoint & 0x3f));
          }
        }
        return bytes;
      }

      // SHA-1算法实现
      function sha1(bytes) {
        let H0 = 0x67452301;
        let H1 = 0xEFCDAB89;
        let H2 = 0x98BADCFE;
        let H3 = 0x10325476;
        let H4 = 0xC3D2E1F0;
        
        const originalLength = bytes.length * 8;
        const paddingLength = (originalLength % 512 < 448) ? 
                              (448 - originalLength % 512) : 
                              (512 + 448 - originalLength % 512);
        
        const padBytes = Math.ceil(paddingLength / 8);
        const paddedData = [...bytes];
        
        // 添加填充位
        paddedData.push(0x80); // 10000000
        for (let i = 1; i < padBytes; i++) {
          paddedData.push(0x00);
        }
        
        // 添加原始长度（64位，大端序）
        paddedData.push(0);
        paddedData.push(0);
        paddedData.push(0);
        paddedData.push(0);
        paddedData.push((originalLength >>> 24) & 0xff);
        paddedData.push((originalLength >>> 16) & 0xff);
        paddedData.push((originalLength >>> 8) & 0xff);
        paddedData.push(originalLength & 0xff);
        
        // 处理每个512位块
        for (let i = 0; i < paddedData.length; i += 64) {
          const w = new Array(80);
          for (let j = 0; j < 16; j++) {
            w[j] = paddedData[i + j * 4] << 24 | 
                   paddedData[i + j * 4 + 1] << 16 | 
                   paddedData[i + j * 4 + 2] << 8 | 
                   paddedData[i + j * 4 + 3];
          }
          
          for (let j = 16; j < 80; j++) {
            w[j] = ((w[j - 3] ^ w[j - 8] ^ w[j - 14] ^ w[j - 16]) << 1) | 
                   ((w[j - 3] ^ w[j - 8] ^ w[j - 14] ^ w[j - 16]) >>> 31);
          }
          
          let a = H0;
          let b = H1;
          let c = H2;
          let d = H3;
          let e = H4;
          
          for (let j = 0; j < 20; j++) {
            const temp = ((a << 5) | (a >>> 27)) + 
                        ((b & c) | (~b & d)) + 
                        e + w[j] + 0x5A827999;
            e = d;
            d = c;
            c = (b << 30) | (b >>> 2);
            b = a;
            a = temp >>> 0;
          }
          
          for (let j = 20; j < 40; j++) {
            const temp = ((a << 5) | (a >>> 27)) + 
                        (b ^ c ^ d) + 
                        e + w[j] + 0x6ED9EBA1;
            e = d;
            d = c;
            c = (b << 30) | (b >>> 2);
            b = a;
            a = temp >>> 0;
          }
          
          for (let j = 40; j < 60; j++) {
            const temp = ((a << 5) | (a >>> 27)) + 
                        ((b & c) | (b & d) | (c & d)) + 
                        e + w[j] + 0x8F1BBCDC;
            e = d;
            d = c;
            c = (b << 30) | (b >>> 2);
            b = a;
            a = temp >>> 0;
          }
          
          for (let j = 60; j < 80; j++) {
            const temp = ((a << 5) | (a >>> 27)) + 
                        (b ^ c ^ d) + 
                        e + w[j] + 0xCA62C1D6;
            e = d;
            d = c;
            c = (b << 30) | (b >>> 2);
            b = a;
            a = temp >>> 0;
          }
          
          H0 = (H0 + a) >>> 0;
          H1 = (H1 + b) >>> 0;
          H2 = (H2 + c) >>> 0;
          H3 = (H3 + d) >>> 0;
          H4 = (H4 + e) >>> 0;
        }
        
        // 返回字节数组
        const result = [];
        result.push((H0 >> 24) & 0xff);
        result.push((H0 >> 16) & 0xff);
        result.push((H0 >> 8) & 0xff);
        result.push(H0 & 0xff);
        result.push((H1 >> 24) & 0xff);
        result.push((H1 >> 16) & 0xff);
        result.push((H1 >> 8) & 0xff);
        result.push(H1 & 0xff);
        result.push((H2 >> 24) & 0xff);
        result.push((H2 >> 16) & 0xff);
        result.push((H2 >> 8) & 0xff);
        result.push(H2 & 0xff);
        result.push((H3 >> 24) & 0xff);
        result.push((H3 >> 16) & 0xff);
        result.push((H3 >> 8) & 0xff);
        result.push(H3 & 0xff);
        result.push((H4 >> 24) & 0xff);
        result.push((H4 >> 16) & 0xff);
        result.push((H4 >> 8) & 0xff);
        result.push(H4 & 0xff);
        
        return result;
      }

      // HMAC实现
      function hmac(keyStr, messageStr) {
        const keyBytes = stringToUtf8Bytes(keyStr);
        const messageBytes = stringToUtf8Bytes(messageStr);
        
        // 对密钥进行填充或截断
        let key = new Array(blockSize).fill(0);
        if (keyBytes.length > blockSize) {
          // 如果密钥太长，先对其进行SHA-1哈希
          const hash = sha1(keyBytes);
          for (let i = 0; i < hash.length; i++) {
            key[i] = hash[i];
          }
        } else {
          // 否则直接复制密钥
          for (let i = 0; i < keyBytes.length; i++) {
            key[i] = keyBytes[i];
          }
        }
        
        // 创建ipad和opad
        const ipad = new Array(blockSize);
        const opad = new Array(blockSize);
        for (let i = 0; i < blockSize; i++) {
          ipad[i] = key[i] ^ 0x36;
          opad[i] = key[i] ^ 0x5C;
        }
        
        // 计算HMAC
        const innerData = [...ipad, ...messageBytes];
        const innerHash = sha1(innerData);
        const outerData = [...opad, ...innerHash];
        const outerHash = sha1(outerData);
        
        return outerHash;
      }

      // 执行HMAC计算
      const hmacResult = hmac(encryptKey, encryptText);
      
      // 将字节数组转换为Base64
      function bytesToBase64(bytes) {
        const b64chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
        let result = '';
        
        for (let i = 0; i < bytes.length; i += 3) {
          const a = bytes[i];
          const b = i + 1 < bytes.length ? bytes[i + 1] : 0;
          const c = i + 2 < bytes.length ? bytes[i + 2] : 0;
          
          result += b64chars[a >> 2];
          result += b64chars[((a & 3) << 4) | (b >> 4)];
          result += i + 1 < bytes.length ? b64chars[((b & 15) << 2) | (c >> 6)] : '=';
          result += i + 2 < bytes.length ? b64chars[c & 63] : '=';
        }
        
        return result;
      }
      
      console.log('HMAC字节数组长度:', hmacResult.length);
      const base64Result = bytesToBase64(hmacResult);
      console.log('Base64编码结果:', base64Result);
      console.log('===== HMAC-SHA1加密完成 =====');
      
      return base64Result;
    } catch (error) {
      console.error('HmacSHA1加密失败:', error);
      throw error;
    }
  }



  /**
   * 生成WebSocket鉴权URL
   * @param {string} baseUrl - WebSocket基础URL
   * @returns {string} 带鉴权参数的WebSocket URL
   */
  async generateWebSocketUrl(baseUrl) {
    try {
      const { timestamp, signature } = await this.getAuthInfo();
      // 按照Main.java中的URL构建方式
      return `${baseUrl}?appId=${this.appId}&timestamp=${timestamp}&signature=${signature}`;
    } catch (error) {
      console.error('生成WebSocket URL失败:', error);
      throw error;
    }
  }

  /**
   * 生成HTTP请求头
   * @returns {Object} HTTP请求头对象
   */
  async generateHttpHeaders() {
    try {
      // 直接按照Main.java中的请求头格式
      const { timestamp, signature } = await this.getAuthInfo();
      
      return {
        'appId': this.appId,
        'timestamp': timestamp,
        'signature': signature
      };
    } catch (error) {
      console.error('生成HTTP请求头失败:', error);
      throw error;
    }
  }
}

export default AuthService;