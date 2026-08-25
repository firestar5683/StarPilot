#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_7992688260990922493);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_5809721741941332225);
void pose_H_mod_fun(double *state, double *out_653094641834631323);
void pose_f_fun(double *state, double dt, double *out_5955110383788875610);
void pose_F_fun(double *state, double dt, double *out_3374367099061520939);
void pose_h_4(double *state, double *unused, double *out_583201360619966174);
void pose_H_4(double *state, double *unused, double *out_402417908502924402);
void pose_h_10(double *state, double *unused, double *out_356753245810915962);
void pose_H_10(double *state, double *unused, double *out_7727584574864679993);
void pose_h_13(double *state, double *unused, double *out_1340717926179505345);
void pose_H_13(double *state, double *unused, double *out_7208213299813776527);
void pose_h_14(double *state, double *unused, double *out_4852912044053324854);
void pose_H_14(double *state, double *unused, double *out_3560822947836560127);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}