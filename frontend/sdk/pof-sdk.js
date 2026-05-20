export class POFClient {
  constructor(options = {}) {
    this.baseUrl = (options.baseUrl || 'http://localhost:8000').replace(/\/$/, '');
    this.timeout = options.timeout || 30000;
  }

  async healthCheck() {
    return this._request('/health', {
      method: 'GET'
    });
  }

  async verify({
    userId,
    scenario = 'approved',
    videoFile,
    poiImageFile
  }) {
    if (!userId) {
      throw new Error('userId is required');
    }

    if (!videoFile) {
      throw new Error('videoFile is required');
    }

    if (!poiImageFile) {
      throw new Error('poiImageFile is required');
    }

    if (!videoFile.name.toLowerCase().endsWith('.mp4')) {
      throw new Error('Only MP4 video is supported');
    }

    if (videoFile.size > 10 * 1024 * 1024) {
      throw new Error('Video file too large, max 10MB');
    }

    const imageName = poiImageFile.name.toLowerCase();
    const allowedImages = ['.jpg', '.jpeg', '.png', '.webp'];

    if (!allowedImages.some((ext) => imageName.endsWith(ext))) {
      throw new Error('Only JPG, JPEG, PNG or WEBP POI image is supported');
    }

    if (poiImageFile.size > 5 * 1024 * 1024) {
      throw new Error('POI image too large, max 5MB');
    }

    const formData = new FormData();
    formData.append('video', videoFile);
    formData.append('poi_image', poiImageFile);

    const params = new URLSearchParams({
      user_id: userId,
      scenario
    });

    return this._request(`/api/v1/verify?${params.toString()}`, {
      method: 'POST',
      body: formData
    });
  }

  async _request(path, options) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(`${this.baseUrl}${path}`, {
        ...options,
        signal: controller.signal
      });

      const text = await response.text();

      let data;

      try {
        data = text ? JSON.parse(text) : null;
      } catch {
        data = text;
      }

      if (!response.ok) {
        const message = data?.detail || data?.message || `HTTP ${response.status}`;
        throw new Error(typeof message === 'string' ? message : JSON.stringify(message));
      }

      return data;
    } catch (error) {
      if (error.name === 'AbortError') {
        throw new Error('Request timeout');
      }

      throw error;
    } finally {
      clearTimeout(timer);
    }
  }
}

export function getDecisionMessage(result) {
  const percent = (value) => {
    return typeof value === 'number' ? `${Math.round(value * 100)}%` : '-';
  };

  const scoreText =
    `综合置信度 ${percent(result.confidence_score)}，` +
    `人脸相似度 ${percent(result.similarity_score)}，` +
    `活体分数 ${percent(result.liveness_score)}，` +
    `视频质量 ${percent(result.quality_score)}。`;

  if (result.decision === 'approved') {
    return {
      type: 'success',
      title: '验证通过',
      message: `身份验证已通过。${scoreText}`
    };
  }

  if (result.decision === 'manual_review') {
    return {
      type: 'warning',
      title: '需人工审核',
      message: `系统无法自动确认，请进入人工审核流程。${scoreText}`
    };
  }

  return {
    type: 'error',
    title: '验证未通过',
    message: `${result.reason || '请重新录制视频后再试。'} ${scoreText}`
  };
}