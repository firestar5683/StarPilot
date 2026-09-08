#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_7754318151462489406);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_5172808168415891616);
void pose_H_mod_fun(double *state, double *out_2254475305049299983);
void pose_f_fun(double *state, double dt, double *out_9187930556967356165);
void pose_F_fun(double *state, double dt, double *out_1250378920670806697);
void pose_h_4(double *state, double *unused, double *out_3431796064752050994);
void pose_H_4(double *state, double *unused, double *out_1019746773741649270);
void pose_h_10(double *state, double *unused, double *out_4742817048768310237);
void pose_H_10(double *state, double *unused, double *out_7482829619336622044);
void pose_h_13(double *state, double *unused, double *out_3124060736866225144);
void pose_H_13(double *state, double *unused, double *out_2192527051590683531);
void pose_h_14(double *state, double *unused, double *out_3873502266244196496);
void pose_H_14(double *state, double *unused, double *out_2943494082597835259);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}