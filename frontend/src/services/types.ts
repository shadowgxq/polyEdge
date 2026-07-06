/**
 * 数据层基座类型（PRD §1.4 / §5.2）。
 *
 * 与后端统一响应契约对齐（docs/backend/standards/api-and-error-contract.md）：
 * 所有接口返回 `{ code, message, data }` 信封，客户端只解析这一种结构。
 * 下游功能页在各自模块内写 `*.api.ts`（经 shared/api 的 `request`）+ `*.queries.ts`
 * 消费本处约定的类型，不在组件内直接发请求、不另造平行信封类型。
 */

/** ISO 8601 时间字符串（后端时间统一用 ISO 8601）。 */
export type IsoDateTimeString = string;

/** 后端统一响应信封：成功 code=0。 */
export type ApiResponseDto<TData> = {
  code: number;
  message: string;
  data: TData;
};

/** 分页信封（后端 `Paginated[T]`，snake_case 对齐）。 */
export type PaginatedDto<TItem> = {
  list: TItem[];
  total: number;
  page: number;
  page_size: number;
};
