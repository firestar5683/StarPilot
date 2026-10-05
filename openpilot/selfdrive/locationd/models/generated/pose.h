#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_6249615963109186962);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_7563571606094106109);
void pose_H_mod_fun(double *state, double *out_3216188353717940043);
void pose_f_fun(double *state, double dt, double *out_6979270288524198339);
void pose_F_fun(double *state, double dt, double *out_6492284477154870567);
void pose_h_4(double *state, double *unused, double *out_9173610292480735262);
void pose_H_4(double *state, double *unused, double *out_6987995563561847615);
void pose_h_10(double *state, double *unused, double *out_4580681428320651947);
void pose_H_10(double *state, double *unused, double *out_4215236079406633816);
void pose_h_13(double *state, double *unused, double *out_7612834127399631628);
void pose_H_13(double *state, double *unused, double *out_3848117301831003072);
void pose_h_14(double *state, double *unused, double *out_6844612447345845382);
void pose_H_14(double *state, double *unused, double *out_3905207131266475319);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}