import type { ApiResponseDto } from '../../../services/types';
import { request } from '../../../shared/api';
import type { PosterImage, UploadedPosterImage } from './sharePoster.types';

type UploadedPosterImageDto = {
  url: string;
  path: string;
  content_type: string;
  size: number;
};

function toUploadedPosterImage(dto: UploadedPosterImageDto): UploadedPosterImage {
  return {
    url: dto.url,
    path: dto.path,
    contentType: dto.content_type,
    size: dto.size,
  };
}

export async function uploadPosterImage(image: PosterImage): Promise<UploadedPosterImage> {
  const response = await request<ApiResponseDto<UploadedPosterImageDto>, Blob>({
    method: 'POST',
    url: '/api/v1/uploads/images',
    data: image.blob,
    headers: {
      'Content-Type': image.blob.type || 'image/png',
    },
    timeout: 20000,
  });

  return toUploadedPosterImage(response.data);
}
