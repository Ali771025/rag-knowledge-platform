import { requestApi } from "./client";

export interface UserProfileResponse {
  id: string;
  user_id: string;
  knowledge_level?: string;
  personality_type?: string | null;
  preferred_response_style?: string;
  onboarding_progress?: number;
  last_state?: string;
  completed_milestones?: string[];
  engagement_score?: number;
  total_messages?: number;
  total_sessions?: number;
  last_active_at?: string | null;
  language: string;
  timezone?: string;
  updated_at?: string;
  created_at?: string;
}

export interface UpdateUserProfilePayload {
  language?: string;
}

const USER_PROFILE_ENDPOINTS = {
  profile: "/v1/users/profile"
} as const;

export async function getUserProfile(): Promise<UserProfileResponse> {
  return requestApi<UserProfileResponse>({
    method: "GET",
    url: USER_PROFILE_ENDPOINTS.profile
  });
}

export async function updateUserProfile(payload: UpdateUserProfilePayload): Promise<UserProfileResponse> {
  return requestApi<UserProfileResponse, UpdateUserProfilePayload>({
    method: "PATCH",
    url: USER_PROFILE_ENDPOINTS.profile,
    data: payload
  });
}
