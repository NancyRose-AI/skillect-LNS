export type LeadStatus =
  | "new"
  | "contacted"
  | "qualified"
  | "hot"
  | "closed";

export type Conversation = {
  id: string;
  sender: "lead" | "ai";
  message: string;
  created_at: string;
};

export type Lead = {
  id: string;
  name: string;
  email: string;
  phone: string;
  source: string;
  status: LeadStatus;
  score: number;
  created_at: string;
  conversations: Conversation[];
};
