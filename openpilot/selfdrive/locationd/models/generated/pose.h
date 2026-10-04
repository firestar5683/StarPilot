#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_6914886810623359485);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_1955170315450325036);
void pose_H_mod_fun(double *state, double *out_6464744367615017758);
void pose_f_fun(double *state, double dt, double *out_843490903718422953);
void pose_F_fun(double *state, double dt, double *out_8919071219298160156);
void pose_h_4(double *state, double *unused, double *out_173130356706362345);
void pose_H_4(double *state, double *unused, double *out_3243803474011544720);
void pose_h_10(double *state, double *unused, double *out_3220967759669022070);
void pose_H_10(double *state, double *unused, double *out_7792322668041282962);
void pose_h_13(double *state, double *unused, double *out_5680375753611876010);
void pose_H_13(double *state, double *unused, double *out_31529648679211919);
void pose_h_14(double *state, double *unused, double *out_1831988150759010376);
void pose_H_14(double *state, double *unused, double *out_719437382327939809);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}