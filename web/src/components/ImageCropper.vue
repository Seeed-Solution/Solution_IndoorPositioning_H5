<!-- web/src/components/ImageCropper.vue -->
<template>
  <div class="image-cropper-container">
    <div class="cropper-header">
      <h3>{{ title || t('imageCropper.title') }}</h3>
      <button v-if="showClose" @click="handleClose" class="close-btn">×</button>
    </div>
    
    <div class="cropper-controls">
      
      <!-- 操作按钮 -->
      <div class="control-group">
        <button @click="resetCropper" class="action-btn" :title="t('imageCropper.reset')">
          <span>↺</span> {{ t('imageCropper.reset') }}
        </button>
        <button @click="zoomIn" class="action-btn" :title="t('imageCropper.zoomIn')">
          <span>+</span> {{ t('imageCropper.zoomIn') }}
        </button>
        <button @click="zoomOut" class="action-btn" :title="t('imageCropper.zoomOut')">
          <span>-</span> {{ t('imageCropper.zoomOut') }}
        </button>
      </div>
    </div>
    
    <!-- 裁剪区域 -->
    <div class="cropper-wrapper" ref="wrapperRef">
      <canvas 
        ref="canvasRef" 
        class="cropper-canvas"
        @wheel.prevent="handleWheel"
        @mousedown="handleMouseDown"
        @mousemove="handleMouseMove"
        @mouseup="handleMouseUp"
        @mouseleave="handleMouseUp"
      ></canvas>
    </div>
    
    <!-- 底部操作栏 -->
    <div class="cropper-footer">
      <button @click="handleCancel" class="btn-cancel">{{ t('imageCropper.cancel') }}</button>
      <button @click="handleCrop" class="btn-confirm">{{ t('imageCropper.confirm') }}</button>
    </div>
    
    <!-- 预览区域（可选） -->
    <div v-if="previewImage" class="preview-section">
      <h4>{{ t('imageCropper.preview') }}</h4>
      <img :src="previewImage" :alt="t('imageCropper.previewAlt')" class="preview-img" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

const props = defineProps({
  // 图片源（URL 或 base64）
  imageSrc: {
    type: String,
    required: true
  },
  // 标题
  title: {
    type: String,
    default: null
  },
  // 是否显示关闭按钮
  showClose: {
    type: Boolean,
    default: true
  },
  // 默认裁剪比例（宽/高）
  defaultAspectRatio: {
    type: Number,
    default: null // null 表示自由比例
  },
  // 初始裁剪区域
  initialCropData: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['crop', 'cancel', 'close']);

const canvasRef = ref(null);
const wrapperRef = ref(null);
const previewImage = ref(null);

// 图片对象
const image = ref(null);
// 图片位置和缩放
const imageX = ref(0);
const imageY = ref(0);
const imageScale = ref(1);
// 裁剪框位置和尺寸（相对于 canvas）
const cropBoxX = ref(0);
const cropBoxY = ref(0);
const cropBoxWidth = ref(0);
const cropBoxHeight = ref(0);
// 鼠标拖拽状态
const isDragging = ref(false);
const isDraggingCropBox = ref(false); // 是否正在拖拽裁剪框
const dragStartX = ref(0);
const dragStartY = ref(0);
const dragStartImageX = ref(0);
const dragStartImageY = ref(0);
const dragStartCropBoxX = ref(0);
const dragStartCropBoxY = ref(0);
const dragStartCropBoxWidth = ref(0);
const dragStartCropBoxHeight = ref(0);
const dragCorner = ref(null); // 拖拽的角：'nw', 'ne', 'sw', 'se'

// 当前裁剪比例
const currentAspectRatio = ref(props.defaultAspectRatio);

// 计算比例显示文本 - 直接显示长宽比（像素值）
const cropperAspectRatioDisplay = computed(() => {
  if (!currentAspectRatio.value) {
    // 自由比例时显示实际像素尺寸
    return `${Math.round(cropBoxWidth.value)} : ${Math.round(cropBoxHeight.value)}`;
  }
  // 显示裁剪框的实际像素尺寸
  const width = Math.round(cropBoxWidth.value);
  const height = Math.round(cropBoxHeight.value);
  return `${width} : ${height}`;
});

// 初始化裁剪框
const initCropBox = () => {
  if (!canvasRef.value) return;
  
  const canvas = canvasRef.value;
  const canvasWidth = canvas.width;
  const canvasHeight = canvas.height;
  
  // 裁剪框占 canvas 的 80%
  const maxSize = Math.min(canvasWidth, canvasHeight) * 0.8;
  
  if (currentAspectRatio.value) {
    // 根据比例计算裁剪框尺寸
    const ratio = currentAspectRatio.value;
    let width, height;
    
    if (ratio >= 1) {
      // 横向或正方形
      width = Math.min(maxSize, canvasWidth * 0.8);
      height = width / ratio;
      if (height > canvasHeight * 0.8) {
        height = canvasHeight * 0.8;
        width = height * ratio;
      }
      } else {
      // 纵向
      height = Math.min(maxSize, canvasHeight * 0.8);
      width = height * ratio;
      if (width > canvasWidth * 0.8) {
        width = canvasWidth * 0.8;
        height = width / ratio;
      }
    }
    
    cropBoxWidth.value = width;
    cropBoxHeight.value = height;
  } else {
    // 自由比例，使用正方形
    cropBoxWidth.value = maxSize;
    cropBoxHeight.value = maxSize;
  }
  
  // 居中裁剪框
  cropBoxX.value = (canvasWidth - cropBoxWidth.value) / 2;
  cropBoxY.value = (canvasHeight - cropBoxHeight.value) / 2;
  
  // 如果图片已加载，应用位置限制
  if (image.value) {
    constrainImagePosition();
  }
};

// 加载图片
const loadImage = () => {
  if (!props.imageSrc) return;
  
  // 确保 canvas 尺寸已设置
  if (!canvasRef.value || canvasRef.value.width === 0 || canvasRef.value.height === 0) {
    // 如果 canvas 尺寸还未设置，等待 nextTick 后再加载
    nextTick(() => {
      if (canvasRef.value && canvasRef.value.width > 0 && canvasRef.value.height > 0) {
        loadImage();
      }
    });
    return;
  }
  
  const img = new Image();
  img.crossOrigin = 'anonymous';
  img.onload = () => {
    image.value = img;
    // 先初始化裁剪框（需要先有裁剪框尺寸才能计算图片缩放）
    initCropBox();
    // 然后初始化图片位置和缩放（此时裁剪框已初始化）
    resetImageTransform();
    // 最后绘制
    draw();
  };
  img.onerror = () => {
    console.error(t('imageCropper.imageLoadFailed'));
  };
  img.src = props.imageSrc;
};

// 计算图片的最小缩放比例（确保图片能覆盖整个裁剪框）
const getMinScale = () => {
  if (!image.value || !canvasRef.value) return 0.1;
  
  const img = image.value;
  const cropWidth = cropBoxWidth.value;
  const cropHeight = cropBoxHeight.value;
  
  // 计算需要覆盖裁剪框的最小缩放比例
  const scaleX = cropWidth / img.width;
  const scaleY = cropHeight / img.height;
  
  // 返回较大的比例，确保图片能完全覆盖裁剪框
  return Math.max(scaleX, scaleY);
};

// 限制图片位置，确保裁剪框内始终有图片内容
const constrainImagePosition = () => {
  if (!image.value || !canvasRef.value) return;
  
  const img = image.value;
  const canvas = canvasRef.value;
  const scale = imageScale.value;
  const imgWidth = img.width * scale;
  const imgHeight = img.height * scale;
  
  // 裁剪框的四个角坐标
  const cropLeft = cropBoxX.value;
  const cropTop = cropBoxY.value;
  const cropRight = cropBoxX.value + cropBoxWidth.value;
  const cropBottom = cropBoxY.value + cropBoxHeight.value;
  
  // 图片的四个角坐标
  const imgLeft = imageX.value;
  const imgTop = imageY.value;
  const imgRight = imageX.value + imgWidth;
  const imgBottom = imageY.value + imgHeight;
  
  // 限制图片位置，确保裁剪框的四个角都在图片范围内
  // 如果裁剪框的左上角在图片外，向右下移动图片
  if (cropLeft < imgLeft) {
    imageX.value = cropLeft;
  }
  if (cropTop < imgTop) {
    imageY.value = cropTop;
  }
  
  // 如果裁剪框的右下角在图片外，向左上移动图片
  if (cropRight > imgRight) {
    imageX.value = cropRight - imgWidth;
  }
  if (cropBottom > imgBottom) {
    imageY.value = cropBottom - imgHeight;
  }
  
  // 重新计算（因为上面的调整可能影响另一个方向）
  const newImgLeft = imageX.value;
  const newImgTop = imageY.value;
  const newImgRight = imageX.value + imgWidth;
  const newImgBottom = imageY.value + imgHeight;
  
  // 再次检查并调整，确保所有角都在范围内
  if (cropLeft < newImgLeft) {
    imageX.value = cropLeft;
  }
  if (cropRight > newImgRight) {
    imageX.value = cropRight - imgWidth;
  }
  if (cropTop < newImgTop) {
    imageY.value = cropTop;
  }
  if (cropBottom > newImgBottom) {
    imageY.value = cropBottom - imgHeight;
  }
};

// 重置图片变换
const resetImageTransform = () => {
  if (!image.value || !canvasRef.value) return;
  
  const canvas = canvasRef.value;
  const img = image.value;
  
  // 计算合适的初始缩放比例，使图片能够覆盖裁剪框
  const minScale = getMinScale();
  imageScale.value = minScale * 1.2; // 稍微放大一点，方便调整
  
  // 居中图片
  imageX.value = (canvas.width - img.width * imageScale.value) / 2;
  imageY.value = (canvas.height - img.height * imageScale.value) / 2;
  
  // 应用位置限制
  constrainImagePosition();
};

// 绘制
const draw = () => {
  if (!canvasRef.value || !image.value) return;
  
  const canvas = canvasRef.value;
  const ctx = canvas.getContext('2d');
  
  // 清空画布
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  
  // 绘制背景网格
  drawGrid(ctx, canvas.width, canvas.height);
  
  // 保存上下文
  ctx.save();
  
  // 绘制图片
  ctx.drawImage(
    image.value,
    imageX.value,
    imageY.value,
    image.value.width * imageScale.value,
    image.value.height * imageScale.value
  );
  
  // 绘制遮罩层（裁剪框外的区域变暗）
  drawMask(ctx, canvas.width, canvas.height);
  
  // 绘制裁剪框
  drawCropBox(ctx);
  
  // 恢复上下文
  ctx.restore();
};

// 绘制网格背景
const drawGrid = (ctx, width, height) => {
  ctx.fillStyle = '#f5f5f5';
  ctx.fillRect(0, 0, width, height);
  
  const gridSize = 20;
  ctx.strokeStyle = '#e0e0e0';
  ctx.lineWidth = 1;
  
  for (let x = 0; x <= width; x += gridSize) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }
  
  for (let y = 0; y <= height; y += gridSize) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }
};

// 绘制遮罩层
const drawMask = (ctx, width, height) => {
  ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
  ctx.fillRect(0, 0, width, height);
  
  // 清除裁剪框区域
  ctx.globalCompositeOperation = 'destination-out';
  ctx.fillRect(cropBoxX.value, cropBoxY.value, cropBoxWidth.value, cropBoxHeight.value);
  ctx.globalCompositeOperation = 'source-over';
};

// 检测鼠标是否在裁剪框的角上
const getCornerAtPoint = (x, y) => {
  const cornerSize = 16; // 角的可点击区域大小
  const cx = cropBoxX.value;
  const cy = cropBoxY.value;
  const cw = cropBoxWidth.value;
  const ch = cropBoxHeight.value;
  
  // 左上角
  if (x >= cx - cornerSize && x <= cx + cornerSize && 
      y >= cy - cornerSize && y <= cy + cornerSize) {
    return 'nw';
  }
  // 右上角
  if (x >= cx + cw - cornerSize && x <= cx + cw + cornerSize && 
      y >= cy - cornerSize && y <= cy + cornerSize) {
    return 'ne';
  }
  // 左下角
  if (x >= cx - cornerSize && x <= cx + cornerSize && 
      y >= cy + ch - cornerSize && y <= cy + ch + cornerSize) {
    return 'sw';
  }
  // 右下角
  if (x >= cx + cw - cornerSize && x <= cx + cw + cornerSize && 
      y >= cy + ch - cornerSize && y <= cy + ch + cornerSize) {
    return 'se';
  }
  return null;
};

// 绘制裁剪框
const drawCropBox = (ctx) => {
  const x = cropBoxX.value;
  const y = cropBoxY.value;
  const w = cropBoxWidth.value;
  const h = cropBoxHeight.value;
  
  // 绘制边框
  ctx.strokeStyle = '#667eea';
  ctx.lineWidth = 2;
  ctx.setLineDash([]);
  ctx.strokeRect(x, y, w, h);
  
  // 绘制四个角的指示器
  const cornerSize = 12;
  ctx.fillStyle = '#667eea';
  ctx.strokeStyle = '#fff';
  ctx.lineWidth = 2;
  
  // 左上角
  ctx.fillRect(x - 2, y - 2, cornerSize, 4);
  ctx.fillRect(x - 2, y - 2, 4, cornerSize);
  ctx.strokeRect(x - 2, y - 2, cornerSize, 4);
  ctx.strokeRect(x - 2, y - 2, 4, cornerSize);
  
  // 右上角
  ctx.fillRect(x + w - cornerSize + 2, y - 2, cornerSize, 4);
  ctx.fillRect(x + w - 2, y - 2, 4, cornerSize);
  ctx.strokeRect(x + w - cornerSize + 2, y - 2, cornerSize, 4);
  ctx.strokeRect(x + w - 2, y - 2, 4, cornerSize);
  
  // 左下角
  ctx.fillRect(x - 2, y + h - 2, cornerSize, 4);
  ctx.fillRect(x - 2, y + h - cornerSize + 2, 4, cornerSize);
  ctx.strokeRect(x - 2, y + h - 2, cornerSize, 4);
  ctx.strokeRect(x - 2, y + h - cornerSize + 2, 4, cornerSize);
  
  // 右下角
  ctx.fillRect(x + w - cornerSize + 2, y + h - 2, cornerSize, 4);
  ctx.fillRect(x + w - 2, y + h - cornerSize + 2, 4, cornerSize);
  ctx.strokeRect(x + w - cornerSize + 2, y + h - 2, cornerSize, 4);
  ctx.strokeRect(x + w - 2, y + h - cornerSize + 2, 4, cornerSize);
  
  // 绘制辅助线（九宫格）
  ctx.strokeStyle = 'rgba(102, 126, 234, 0.3)';
  ctx.lineWidth = 1;
  ctx.setLineDash([5, 5]);
  
  // 垂直线
  ctx.beginPath();
  ctx.moveTo(x + w / 3, y);
  ctx.lineTo(x + w / 3, y + h);
  ctx.stroke();
  
  ctx.beginPath();
  ctx.moveTo(x + (w * 2) / 3, y);
  ctx.lineTo(x + (w * 2) / 3, y + h);
  ctx.stroke();
  
  // 水平线
  ctx.beginPath();
  ctx.moveTo(x, y + h / 3);
  ctx.lineTo(x + w, y + h / 3);
  ctx.stroke();
  
  ctx.beginPath();
  ctx.moveTo(x, y + (h * 2) / 3);
  ctx.lineTo(x + w, y + (h * 2) / 3);
  ctx.stroke();
};

// 获取鼠标在 canvas 上的坐标
const getCanvasPoint = (e) => {
  if (!canvasRef.value) return { x: 0, y: 0 };
  
  const canvas = canvasRef.value;
  const rect = canvas.getBoundingClientRect();
  return {
    x: e.clientX - rect.left,
    y: e.clientY - rect.top
  };
};

// 鼠标滚轮缩放
const handleWheel = (e) => {
  e.preventDefault();
  
  if (!image.value) return;
  
  const point = getCanvasPoint(e);
  
  // 计算最小缩放比例
  const minScale = getMinScale();
  
  // 使用指数缩放，根据实际滚动量计算缩放增量
  // deltaY 的绝对值越大，缩放幅度越大；但整体幅度更小，便于精确控制
  const zoomSensitivity = 0.0008; // 缩放敏感度，可以调整（值越小越慢）
  const zoomFactor = 1 + (-e.deltaY * zoomSensitivity);
  
  // 应用指数缩放，限制在最小缩放比例和最大缩放比例之间
  const newScale = Math.max(minScale, Math.min(5, imageScale.value * zoomFactor));
  imageScale.value = newScale;
  
  // 计算缩放前的坐标相对于图片的位置
  const imagePointX = (point.x - imageX.value) / imageScale.value;
  const imagePointY = (point.y - imageY.value) / imageScale.value;
  
  // 调整图片位置，使缩放点保持在鼠标位置
  imageX.value = point.x - imagePointX * imageScale.value;
  imageY.value = point.y - imagePointY * imageScale.value;
  
  // 应用位置限制
  constrainImagePosition();
  
  draw();
};

// 鼠标按下
const handleMouseDown = (e) => {
  if (!image.value) return;
  
  const point = getCanvasPoint(e);
  
  // 检查是否点击在裁剪框的角上
  const corner = getCornerAtPoint(point.x, point.y);
  if (corner) {
    // 开始拖拽裁剪框角
    isDraggingCropBox.value = true;
    dragCorner.value = corner;
    dragStartX.value = point.x;
    dragStartY.value = point.y;
    dragStartCropBoxX.value = cropBoxX.value;
    dragStartCropBoxY.value = cropBoxY.value;
    dragStartCropBoxWidth.value = cropBoxWidth.value;
    dragStartCropBoxHeight.value = cropBoxHeight.value;
    
    // 改变鼠标样式
    if (canvasRef.value) {
      canvasRef.value.style.cursor = 'nwse-resize';
    }
    return;
  }
  
  // 拖拽图片
  isDragging.value = true;
  dragStartX.value = point.x;
  dragStartY.value = point.y;
  dragStartImageX.value = imageX.value;
  dragStartImageY.value = imageY.value;
  
  // 改变鼠标样式
  if (canvasRef.value) {
    canvasRef.value.style.cursor = 'grabbing';
  }
};

// 鼠标移动
const handleMouseMove = (e) => {
  if (!image.value) return;
  
  const point = getCanvasPoint(e);
  
  // 如果正在拖拽裁剪框角
  if (isDraggingCropBox.value && dragCorner.value) {
    const deltaX = point.x - dragStartX.value;
    const deltaY = point.y - dragStartY.value;
    
    // 根据拖拽的角和比例调整裁剪框大小
    const aspectRatio = currentAspectRatio.value;
    if (!aspectRatio) {
      // 自由比例，直接调整
      adjustCropBoxFree(deltaX, deltaY);
    } else {
      // 固定比例，按比例调整
      adjustCropBoxWithRatio(deltaX, deltaY, aspectRatio);
    }
    
    draw();
    return;
  }
  
  // 如果正在拖拽图片
  if (isDragging.value) {
    const deltaX = point.x - dragStartX.value;
    const deltaY = point.y - dragStartY.value;
    
    imageX.value = dragStartImageX.value + deltaX;
    imageY.value = dragStartImageY.value + deltaY;
    
    // 应用位置限制
    constrainImagePosition();
    
    draw();
    return;
  }
  
  // 鼠标悬停时改变样式
  const corner = getCornerAtPoint(point.x, point.y);
  if (canvasRef.value) {
    if (corner) {
      // 根据角的位置设置不同的鼠标样式
      const cursorMap = {
        'nw': 'nwse-resize',
        'ne': 'nesw-resize',
        'sw': 'nesw-resize',
        'se': 'nwse-resize'
      };
      canvasRef.value.style.cursor = cursorMap[corner] || 'default';
    } else {
      canvasRef.value.style.cursor = 'grab';
    }
  }
};

// 自由比例调整裁剪框
const adjustCropBoxFree = (deltaX, deltaY) => {
  const corner = dragCorner.value;
  const canvas = canvasRef.value;
  if (!canvas) return;
  
  let newX = dragStartCropBoxX.value;
  let newY = dragStartCropBoxY.value;
  let newWidth = dragStartCropBoxWidth.value;
  let newHeight = dragStartCropBoxHeight.value;
  
  switch (corner) {
    case 'nw': // 左上角
      newX = dragStartCropBoxX.value + deltaX;
      newY = dragStartCropBoxY.value + deltaY;
      newWidth = dragStartCropBoxWidth.value - deltaX;
      newHeight = dragStartCropBoxHeight.value - deltaY;
      break;
    case 'ne': // 右上角
      newY = dragStartCropBoxY.value + deltaY;
      newWidth = dragStartCropBoxWidth.value + deltaX;
      newHeight = dragStartCropBoxHeight.value - deltaY;
      break;
    case 'sw': // 左下角
      newX = dragStartCropBoxX.value + deltaX;
      newWidth = dragStartCropBoxWidth.value - deltaX;
      newHeight = dragStartCropBoxHeight.value + deltaY;
      break;
    case 'se': // 右下角
      newWidth = dragStartCropBoxWidth.value + deltaX;
      newHeight = dragStartCropBoxHeight.value + deltaY;
      break;
  }
  
  // 限制裁剪框在 canvas 范围内
  newX = Math.max(0, Math.min(canvas.width - newWidth, newX));
  newY = Math.max(0, Math.min(canvas.height - newHeight, newY));
  newWidth = Math.max(50, Math.min(canvas.width - newX, newWidth));
  newHeight = Math.max(50, Math.min(canvas.height - newY, newHeight));
  
  cropBoxX.value = newX;
  cropBoxY.value = newY;
  cropBoxWidth.value = newWidth;
  cropBoxHeight.value = newHeight;
  
  // 裁剪框大小改变后，检查并调整图片位置和缩放
  if (image.value) {
    const minScale = getMinScale();
    // 如果当前缩放小于最小缩放，调整到最小缩放
    if (imageScale.value < minScale) {
      imageScale.value = minScale;
    }
    // 应用位置限制
    constrainImagePosition();
  }
};

// 按比例调整裁剪框
const adjustCropBoxWithRatio = (deltaX, deltaY, aspectRatio) => {
  const corner = dragCorner.value;
  const canvas = canvasRef.value;
  if (!canvas) return;
  
  // 获取对角的固定点（不动的角）
  let fixedCornerX, fixedCornerY;
  let newCornerX, newCornerY;
  
  switch (corner) {
    case 'nw': // 左上角 - 固定右下角
      fixedCornerX = dragStartCropBoxX.value + dragStartCropBoxWidth.value;
      fixedCornerY = dragStartCropBoxY.value + dragStartCropBoxHeight.value;
      newCornerX = dragStartCropBoxX.value + deltaX;
      newCornerY = dragStartCropBoxY.value + deltaY;
      break;
    case 'ne': // 右上角 - 固定左下角
      fixedCornerX = dragStartCropBoxX.value;
      fixedCornerY = dragStartCropBoxY.value + dragStartCropBoxHeight.value;
      newCornerX = dragStartCropBoxX.value + dragStartCropBoxWidth.value + deltaX;
      newCornerY = dragStartCropBoxY.value + deltaY;
      break;
    case 'sw': // 左下角 - 固定右上角
      fixedCornerX = dragStartCropBoxX.value + dragStartCropBoxWidth.value;
      fixedCornerY = dragStartCropBoxY.value;
      newCornerX = dragStartCropBoxX.value + deltaX;
      newCornerY = dragStartCropBoxY.value + dragStartCropBoxHeight.value + deltaY;
      break;
    case 'se': // 右下角 - 固定左上角
      fixedCornerX = dragStartCropBoxX.value;
      fixedCornerY = dragStartCropBoxY.value;
      newCornerX = dragStartCropBoxX.value + dragStartCropBoxWidth.value + deltaX;
      newCornerY = dragStartCropBoxY.value + dragStartCropBoxHeight.value + deltaY;
      break;
  }
  
  // 计算新的宽高（基于对角距离）
  let rawWidth = Math.abs(newCornerX - fixedCornerX);
  let rawHeight = Math.abs(newCornerY - fixedCornerY);
  
  // 根据比例调整，保持比例不变
  // 选择较小的变化量来保持比例
  const widthBasedHeight = rawWidth / aspectRatio;
  const heightBasedWidth = rawHeight * aspectRatio;
  
  let newWidth, newHeight;
  if (widthBasedHeight <= rawHeight) {
    // 以宽度为准
    newWidth = rawWidth;
    newHeight = newWidth / aspectRatio;
  } else {
    // 以高度为准
    newHeight = rawHeight;
    newWidth = newHeight * aspectRatio;
  }
  
  // 限制最小尺寸
  const minSize = 50;
  if (aspectRatio >= 1) {
    if (newWidth < minSize) {
      newWidth = minSize;
      newHeight = newWidth / aspectRatio;
    }
  } else {
    if (newHeight < minSize) {
      newHeight = minSize;
      newWidth = newHeight * aspectRatio;
    }
  }
  
  // 计算新位置（保持固定角位置不变）
  let newX, newY;
  switch (corner) {
    case 'nw': // 左上角 - 固定右下角
      newX = fixedCornerX - newWidth;
      newY = fixedCornerY - newHeight;
      break;
    case 'ne': // 右上角 - 固定左下角
      newX = fixedCornerX;
      newY = fixedCornerY - newHeight;
      break;
    case 'sw': // 左下角 - 固定右上角
      newX = fixedCornerX - newWidth;
      newY = fixedCornerY;
      break;
    case 'se': // 右下角 - 固定左上角
      newX = fixedCornerX;
      newY = fixedCornerY;
      break;
  }
  
  // 限制裁剪框在 canvas 范围内
  newX = Math.max(0, Math.min(canvas.width - newWidth, newX));
  newY = Math.max(0, Math.min(canvas.height - newHeight, newY));
  
  // 如果超出边界，调整尺寸
  if (newX + newWidth > canvas.width) {
    newWidth = canvas.width - newX;
    newHeight = newWidth / aspectRatio;
  }
  if (newY + newHeight > canvas.height) {
    newHeight = canvas.height - newY;
    newWidth = newHeight * aspectRatio;
  }
  
  // 再次限制位置（调整后可能超出）
  newX = Math.max(0, Math.min(canvas.width - newWidth, newX));
  newY = Math.max(0, Math.min(canvas.height - newHeight, newY));
  
  cropBoxX.value = newX;
  cropBoxY.value = newY;
  cropBoxWidth.value = newWidth;
  cropBoxHeight.value = newHeight;
  
  // 裁剪框大小改变后，检查并调整图片位置和缩放
  if (image.value) {
    const minScale = getMinScale();
    // 如果当前缩放小于最小缩放，调整到最小缩放
    if (imageScale.value < minScale) {
      imageScale.value = minScale;
    }
    // 应用位置限制
    constrainImagePosition();
  }
};

// 鼠标释放
const handleMouseUp = () => {
  if (isDragging.value) {
    isDragging.value = false;
    if (canvasRef.value) {
      canvasRef.value.style.cursor = 'grab';
    }
  }
  if (isDraggingCropBox.value) {
    isDraggingCropBox.value = false;
    dragCorner.value = null;
    if (canvasRef.value) {
      canvasRef.value.style.cursor = 'grab';
    }
  }
};

// 重置
const resetCropper = () => {
  resetImageTransform();
  initCropBox();
  draw();
};

// 放大
const zoomIn = () => {
  if (!image.value) return;
  const minScale = getMinScale();
  imageScale.value = Math.min(5, imageScale.value + 0.1);
  // 应用位置限制
  constrainImagePosition();
  draw();
};

// 缩小
const zoomOut = () => {
  if (!image.value) return;
  const minScale = getMinScale();
  imageScale.value = Math.max(minScale, imageScale.value - 0.1);
  // 应用位置限制
  constrainImagePosition();
  draw();
};

// 执行裁剪
const handleCrop = () => {
  if (!image.value || !canvasRef.value) return;
  
  const img = image.value;
  
  // 计算裁剪框在原图中的位置和尺寸
  // 裁剪框在 canvas 上的坐标需要转换为在原图上的坐标
  const cropX = (cropBoxX.value - imageX.value) / imageScale.value;
  const cropY = (cropBoxY.value - imageY.value) / imageScale.value;
  const cropWidth = cropBoxWidth.value / imageScale.value;
  const cropHeight = cropBoxHeight.value / imageScale.value;
  
  // 计算裁剪框与图片的交集区域
  const sourceX = Math.max(0, cropX);
  const sourceY = Math.max(0, cropY);
  const sourceEndX = Math.min(img.width, cropX + cropWidth);
  const sourceEndY = Math.min(img.height, cropY + cropHeight);
  
  // 如果裁剪框完全在图片外，不进行裁剪
  if (sourceX >= img.width || sourceY >= img.height || sourceEndX <= 0 || sourceEndY <= 0) {
    console.warn(t('imageCropper.cropBoxOutOfRange'));
    return;
  }
  
  const sourceWidth = sourceEndX - sourceX;
  const sourceHeight = sourceEndY - sourceY;
  
  // 创建新的 canvas 用于输出裁剪后的图片
  // 输出尺寸使用裁剪框的完整尺寸（保持比例）
  const outputCanvas = document.createElement('canvas');
  outputCanvas.width = cropWidth;
  outputCanvas.height = cropHeight;
  const outputCtx = outputCanvas.getContext('2d');
  
  // 设置高质量渲染
  outputCtx.imageSmoothingEnabled = true;
  outputCtx.imageSmoothingQuality = 'high';
  
  // 计算在输出 canvas 上的绘制位置和尺寸
  // 如果裁剪框超出图片，需要调整绘制位置
  const drawX = Math.max(0, -cropX);
  const drawY = Math.max(0, -cropY);
  const drawWidth = sourceWidth;
  const drawHeight = sourceHeight;
  
  // 绘制裁剪后的图片（canvas 默认透明背景，超出部分保持透明）
  outputCtx.drawImage(
    img,
    sourceX, sourceY, drawWidth, drawHeight,
    drawX, drawY, drawWidth, drawHeight
  );
  
  // 转换为 base64（使用 PNG 格式以支持透明背景）
  const croppedImageData = outputCanvas.toDataURL('image/png');
    previewImage.value = croppedImageData;
    
  // 转换为 Blob
  outputCanvas.toBlob((blob) => {
      const result = {
        dataURL: croppedImageData,
        blob: blob,
      canvas: outputCanvas,
      cropData: {
        x: sourceX,
        y: sourceY,
        width: sourceWidth,
        height: sourceHeight
      },
      cropBoxData: {
        left: cropBoxX.value,
        top: cropBoxY.value,
        width: cropBoxWidth.value,
        height: cropBoxHeight.value
      }
      };
      
      emit('crop', result);
    }, 'image/png');
};

// 取消
const handleCancel = () => {
  emit('cancel');
};

// 关闭
const handleClose = () => {
  emit('close');
};

// 调整 canvas 大小
const resizeCanvas = () => {
  if (!canvasRef.value || !wrapperRef.value) return;
  
  const wrapper = wrapperRef.value;
  const canvas = canvasRef.value;
  
  // 设置 canvas 尺寸
  canvas.width = wrapper.clientWidth;
  canvas.height = wrapper.clientHeight;
  
  // 如果图片已加载，重新初始化裁剪框和图片位置，然后绘制
  if (image.value) {
    initCropBox();
    resetImageTransform();
    draw();
  }
};

// 监听图片源变化
watch(() => props.imageSrc, (newSrc) => {
  if (newSrc && canvasRef.value && canvasRef.value.width > 0 && canvasRef.value.height > 0) {
    // 确保 canvas 尺寸已设置后再加载图片
    loadImage();
  } else if (newSrc) {
    // 如果 canvas 尺寸还未设置，等待 nextTick 后再加载
    nextTick(() => {
      if (canvasRef.value && canvasRef.value.width > 0 && canvasRef.value.height > 0) {
        loadImage();
      }
    });
  }
}, { immediate: false });

// 监听默认比例变化
watch(() => props.defaultAspectRatio, (newRatio) => {
  currentAspectRatio.value = newRatio;
  if (canvasRef.value) {
    initCropBox();
    draw();
  }
}, { immediate: false });

// 窗口大小变化时调整 canvas
let resizeObserver = null;

onMounted(() => {
  nextTick(() => {
    if (wrapperRef.value) {
      resizeCanvas();
      
      // 使用 ResizeObserver 监听容器大小变化
      resizeObserver = new ResizeObserver(() => {
        resizeCanvas();
      });
      resizeObserver.observe(wrapperRef.value);
    }
    
    // 设置初始鼠标样式
    if (canvasRef.value) {
      canvasRef.value.style.cursor = 'grab';
    }
    
    // 如果图片源已存在，确保在 canvas 尺寸设置好后再加载
    if (props.imageSrc && !image.value) {
      loadImage();
    }
  });
});

onUnmounted(() => {
  if (resizeObserver && wrapperRef.value) {
    resizeObserver.unobserve(wrapperRef.value);
    resizeObserver.disconnect();
  }
});
</script>

<style scoped>
.image-cropper-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.cropper-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.cropper-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  color: white;
  font-size: 28px;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.close-btn:hover {
  background-color: rgba(255, 255, 255, 0.2);
}

.cropper-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  padding: 16px 20px;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
  align-items: center;
}

.control-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.control-group label {
  font-size: 14px;
  color: #495057;
  font-weight: 500;
  white-space: nowrap;
}

.aspect-ratio-display {
  padding: 6px 12px;
  font-size: 14px;
  font-weight: 500;
  color: #495057;
  background: #f8f9fa;
  border-radius: 4px;
  border: 1px solid #e9ecef;
}

.action-btn {
  padding: 8px 16px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  background: white;
  color: #495057;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 4px;
}

.action-btn:hover {
  background: #667eea;
  color: white;
  border-color: #667eea;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(102, 126, 234, 0.2);
}

.action-btn span {
  font-size: 16px;
  font-weight: bold;
}

.cropper-wrapper {
  position: relative;
  width: 100%;
  min-height: 400px;
  max-height: 600px;
  background: #f8f9fa;
  overflow: hidden;
}

.cropper-canvas {
  display: block;
  width: 100%;
  height: 100%;
  cursor: grab;
}

.cropper-canvas:active {
  cursor: grabbing;
}

.cropper-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  background: #f8f9fa;
  border-top: 1px solid #e9ecef;
}

.btn-cancel,
.btn-confirm {
  padding: 10px 24px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel {
  background: #e9ecef;
  color: #495057;
}

.btn-cancel:hover {
  background: #dee2e6;
}

.btn-confirm {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-confirm:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);
}

.preview-section {
  padding: 20px;
  background: #f8f9fa;
  border-top: 1px solid #e9ecef;
}

.preview-section h4 {
  margin: 0 0 12px 0;
  font-size: 16px;
  color: #495057;
}

.preview-img {
  max-width: 100%;
  max-height: 300px;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}
</style>
