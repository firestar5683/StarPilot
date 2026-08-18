#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_4038237010904669995);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_2572217743337337909);
void pose_H_mod_fun(double *state, double *out_362240871876916223);
void pose_f_fun(double *state, double dt, double *out_844759421205290898);
void pose_F_fun(double *state, double dt, double *out_3409614379123282877);
void pose_h_4(double *state, double *unused, double *out_3761995773053554002);
void pose_H_4(double *state, double *unused, double *out_4790277513162164512);
void pose_h_10(double *state, double *unused, double *out_1433439433765456745);
void pose_H_10(double *state, double *unused, double *out_2492873908575038793);
void pose_h_13(double *state, double *unused, double *out_7701755112567992010);
void pose_H_13(double *state, double *unused, double *out_8002551338494497313);
void pose_h_14(double *state, double *unused, double *out_3517024732190759371);
void pose_H_14(double *state, double *unused, double *out_1707489080866792216);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}