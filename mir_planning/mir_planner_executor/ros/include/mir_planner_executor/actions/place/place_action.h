/*
 * Copyright [2017] <Bonn-Rhein-Sieg University>
 *
 * Author: Torsten Jandt
 *
 */

#pragma once

#include <mir_planner_executor/actions/executor_action.h>

class PlaceAction : public ExecutorAction
{
 public:
  PlaceAction();

 protected:
  void updateParamsBasedOnContext(std::vector<diagnostic_msgs::KeyValue> &params) override;
  void update_knowledge_base(bool success, std::vector<diagnostic_msgs::KeyValue> &params) override;
};
